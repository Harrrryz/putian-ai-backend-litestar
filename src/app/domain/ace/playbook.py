"""Playbook orchestration and domain-level helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Sequence

import structlog
from sqlalchemy import Select, select
from app.db import models as m

from .delta import DeltaAction, DeltaOperation
from .services import (
    AcePlaybookBulletService,
    AcePlaybookRevisionService,
    AcePlaybookSectionService,
)

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class PlaybookBullet:
    """Serializable snapshot for a playbook bullet."""

    bullet_id: str
    section_name: str
    section_display_name: str
    content: str
    helpful_count: int
    harmful_count: int
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class PlaybookSection:
    """Serializable snapshot for a playbook section."""

    name: str
    display_name: str
    description: str | None
    ordering: int
    metadata: dict[str, Any]
    bullet_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlaybookSnapshot:
    """Ordered representation of sections and bullet lookups."""

    sections: dict[str, PlaybookSection] = field(default_factory=dict)
    bullets: dict[str, PlaybookBullet] = field(default_factory=dict)


@dataclass(slots=True)
class PlaybookDeltaResult:
    """Summary of mutations applied to the playbook."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    tagged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    revision_id: str | None = None

    def has_changes(self) -> bool:
        return any((self.added, self.updated, self.tagged, self.removed))


class AcePlaybookService(AcePlaybookBulletService):
    """High-level operations for loading and mutating playbook state."""

    async def get_snapshot(self, section_names: Sequence[str] | None = None) -> PlaybookSnapshot:
        """Load sections/bullets, preserving ordering for downstream prompts."""
        section_service = self._section_service()
        bullet_stmt: Select[m.AcePlaybookBullet] = select(m.AcePlaybookBullet).order_by(
            m.AcePlaybookBullet.created_at.asc()
        )
        section_stmt: Select[m.AcePlaybookSection] = select(m.AcePlaybookSection).order_by(
            m.AcePlaybookSection.ordering.asc(),
            m.AcePlaybookSection.name.asc(),
        )

        if section_names:
            section_stmt = section_stmt.where(m.AcePlaybookSection.name.in_(section_names))
            bullet_stmt = bullet_stmt.join(m.AcePlaybookBullet.section).where(
                m.AcePlaybookSection.name.in_(section_names)
            )

        sections = await section_service.list(statement=section_stmt)
        bullets = await self.list(statement=bullet_stmt)
        snapshot = PlaybookSnapshot()

        for section in sections:
            snapshot.sections[section.name] = PlaybookSection(
                name=section.name,
                display_name=section.display_name,
                description=section.description,
                ordering=section.ordering,
                metadata=dict(section.metadata_ or {}),
            )

        for bullet in bullets:
            section_name = bullet.section.name
            section_display_name = bullet.section.display_name
            snapshot.bullets[bullet.bullet_id] = PlaybookBullet(
                bullet_id=bullet.bullet_id,
                section_name=section_name,
                section_display_name=section_display_name,
                content=bullet.content,
                helpful_count=bullet.helpful_count,
                harmful_count=bullet.harmful_count,
                metadata=dict(bullet.metadata_ or {}),
                created_at=bullet.created_at,
            )
            section_snapshot = snapshot.sections.get(section_name)
            if section_snapshot:
                section_snapshot.bullet_ids.append(bullet.bullet_id)
            else:
                # Section filtered out but bullet requested, so synthesize entry.
                snapshot.sections[section_name] = PlaybookSection(
                    name=section_name,
                    display_name=section_display_name,
                    description=bullet.section.description,
                    ordering=bullet.section.ordering,
                    metadata=dict(bullet.section.metadata_ or {}),
                    bullet_ids=[bullet.bullet_id],
                )
        return snapshot

    async def apply_deltas(
        self,
        operations: Iterable[DeltaOperation],
        *,
        applied_by: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PlaybookDeltaResult:
        """Apply curator deltas atomically and record a revision entry."""
        deduped = self._deduplicate_ops(operations)
        result = PlaybookDeltaResult()
        if not deduped:
            return result

        section_service = self._section_service()
        revision_service = self._revision_service()
        session = self.repository.session  # type: ignore[attr-defined]
        in_transaction = bool(getattr(session, "in_transaction", lambda: False)())
        transaction = session.begin_nested() if in_transaction else session.begin()

        async with transaction:
            for delta in deduped:
                if delta.action is DeltaAction.ADD:
                    bullet = await self._apply_add(delta, section_service)
                    result.added.append(bullet.bullet_id)
                    continue
                if delta.action is DeltaAction.UPDATE:
                    bullet = await self._apply_update(delta, section_service)
                    if bullet:
                        result.updated.append(bullet.bullet_id)
                    else:
                        result.skipped.append(delta.bullet_id)
                    continue
                if delta.action is DeltaAction.TAG:
                    bullet = await self._apply_tag(delta)
                    if bullet:
                        result.tagged.append(bullet.bullet_id)
                    else:
                        result.skipped.append(delta.bullet_id)
                    continue
                if delta.action is DeltaAction.REMOVE:
                    removed = await self._apply_remove(delta)
                    if removed:
                        result.removed.append(delta.bullet_id)
                    else:
                        result.skipped.append(delta.bullet_id)

            if result.has_changes():
                revision = await revision_service.create(
                    {
                        "operations": [op.model_dump() for op in deduped],
                        "description": description,
                        "applied_by": applied_by,
                        "metadata_": metadata or {},
                    },
                    auto_commit=False,
                )
                result.revision_id = str(revision.id)

        if result.skipped:
            await logger.awarn("Skipped ACE playbook deltas", bullet_ids=result.skipped)
        return result

    def _section_service(self) -> AcePlaybookSectionService:
        return AcePlaybookSectionService(
            session=self.repository.session,  # type: ignore[arg-type,attr-defined]
        )

    def _revision_service(self) -> AcePlaybookRevisionService:
        return AcePlaybookRevisionService(
            session=self.repository.session,  # type: ignore[arg-type,attr-defined]
        )

    def _deduplicate_ops(self, operations: Iterable[DeltaOperation]) -> list[DeltaOperation]:
        deduped: dict[tuple[DeltaAction, str], DeltaOperation] = {}
        for op in operations:
            key = op.dedupe_key()
            if op.action is DeltaAction.TAG and key in deduped:
                existing = deduped[key]
                existing.helpful_delta += op.helpful_delta
                existing.harmful_delta += op.harmful_delta
            else:
                deduped[key] = op.model_copy(deep=True)
        return list(deduped.values())

    async def _apply_add(
        self,
        delta: DeltaOperation,
        section_service: AcePlaybookSectionService,
    ) -> m.AcePlaybookBullet:
        assert delta.section_name and delta.content  # validated upstream
        section = await section_service.get_or_create(
            delta.section_name,
            display_name=delta.section_display_name,
        )
        data = {
            "bullet_id": delta.bullet_id,
            "content": delta.content,
            "section_id": section.id,
            "metadata_": delta.metadata or {},
            "helpful_count": max(delta.helpful_delta, 0),
            "harmful_count": max(delta.harmful_delta, 0),
        }
        existing = await self.get_one_or_none(m.AcePlaybookBullet.bullet_id == delta.bullet_id)
        if existing:
            return await self.update(data=data, item_id=existing.id)
        return await self.create(data, auto_commit=False)

    async def _apply_update(
        self,
        delta: DeltaOperation,
        section_service: AcePlaybookSectionService,
    ) -> m.AcePlaybookBullet | None:
        bullet = await self.get_one_or_none(m.AcePlaybookBullet.bullet_id == delta.bullet_id)
        if not bullet:
            return None
        updates: dict[str, Any] = {}
        if delta.content:
            updates["content"] = delta.content
        if delta.metadata is not None:
            updates["metadata_"] = delta.metadata
        if delta.section_name:
            section = await section_service.get_or_create(
                delta.section_name,
                display_name=delta.section_display_name,
            )
            updates["section_id"] = section.id
        if not updates:
            return bullet
        return await self.update(data=updates, item_id=bullet.id)

    async def _apply_tag(self, delta: DeltaOperation) -> m.AcePlaybookBullet | None:
        bullet = await self.get_one_or_none(m.AcePlaybookBullet.bullet_id == delta.bullet_id)
        if not bullet:
            return None
        new_helpful = max(0, bullet.helpful_count + delta.helpful_delta)
        new_harmful = max(0, bullet.harmful_count + delta.harmful_delta)
        return await self.update(
            data={
                "helpful_count": new_helpful,
                "harmful_count": new_harmful,
            },
            item_id=bullet.id,
        )

    async def _apply_remove(self, delta: DeltaOperation) -> bool:
        bullet = await self.get_one_or_none(m.AcePlaybookBullet.bullet_id == delta.bullet_id)
        if not bullet:
            return False
        await self.delete(bullet.id)
        return True


__all__ = (
    "AcePlaybookService",
    "PlaybookBullet",
    "PlaybookDeltaResult",
    "PlaybookSection",
    "PlaybookSnapshot",
)
