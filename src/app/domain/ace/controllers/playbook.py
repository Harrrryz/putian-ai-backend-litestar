"""HTTP controller for ACE playbook management."""

from __future__ import annotations

from typing import Annotated

import app.db.models as m
from litestar import Controller, get, post
from litestar.di import Provide
from litestar.params import Dependency, Parameter
from sqlalchemy import select

from app.domain.ace import urls
from app.domain.ace.deps import (
    provide_ace_playbook_revision_service,
    provide_ace_playbook_service,
)
from app.domain.ace.playbook import AcePlaybookService, PlaybookSnapshot
from app.domain.ace.schemas import (
    PlaybookBulletRead,
    PlaybookDeltaApplyRequest,
    PlaybookDeltaApplyResponse,
    PlaybookRevisionRead,
    PlaybookSectionRead,
    PlaybookSnapshotRead,
)
from app.domain.ace.services import AcePlaybookRevisionService


class AcePlaybookController(Controller):
    """Expose playbook APIs for ACE orchestration."""

    path = urls.ACE_PLAYBOOK_BASE
    tags = ["ACE"]
    dependencies = {
        "playbook_service": Provide(provide_ace_playbook_service),
        "revision_service": Provide(provide_ace_playbook_revision_service),
    }

    @get(path="/sections", operation_id="ace_list_playbook_sections")
    async def list_sections(
        self,
        playbook_service: Annotated[
            AcePlaybookService, Dependency(skip_validation=True)
        ],
    ) -> PlaybookSnapshotRead:
        """Return the ordered playbook snapshot."""
        snapshot = await playbook_service.get_snapshot()
        return self._serialize_snapshot(snapshot)

    @get(path="/revisions", operation_id="ace_list_playbook_revisions")
    async def list_revisions(
        self,
        revision_service: Annotated[
            AcePlaybookRevisionService, Dependency(skip_validation=True)
        ],
        limit: Annotated[int, Parameter(query="limit")] = 20,
    ) -> list[PlaybookRevisionRead]:
        """Return recent revision entries for auditing."""
        stmt = (
            select(m.AcePlaybookRevision)
            .order_by(m.AcePlaybookRevision.created_at.desc())
            .limit(limit)
        )
        revisions = await revision_service.list(statement=stmt)
        return [
            PlaybookRevisionRead.model_validate(revision)
            for revision in revisions
        ]

    @post(path="/delta", operation_id="ace_apply_playbook_delta")
    async def apply_delta(
        self,
        data: PlaybookDeltaApplyRequest,
        current_user: m.User,
        playbook_service: Annotated[
            AcePlaybookService, Dependency(skip_validation=True)
        ],
    ) -> PlaybookDeltaApplyResponse:
        """Apply curator-style deltas via the API."""
        metadata = data.metadata or {}
        metadata.setdefault("source", "api")
        result = await playbook_service.apply_deltas(
            data.operations,
            applied_by=data.applied_by or str(current_user.id),
            description=data.description,
            metadata=metadata,
        )
        return PlaybookDeltaApplyResponse(result=result)

    @staticmethod
    def _serialize_snapshot(snapshot: PlaybookSnapshot) -> PlaybookSnapshotRead:
        bullet_payloads: dict[str, PlaybookBulletRead] = {}
        for bullet in snapshot.bullets.values():
            bullet_payloads[bullet.bullet_id] = PlaybookBulletRead(
                bullet_id=bullet.bullet_id,
                section_name=bullet.section_name,
                section_display_name=bullet.section_display_name,
                content=bullet.content,
                helpful_count=bullet.helpful_count,
                harmful_count=bullet.harmful_count,
                metadata_=bullet.metadata,
                created_at=bullet.created_at,
            )

        section_payloads: list[PlaybookSectionRead] = []
        sorted_sections = sorted(
            snapshot.sections.values(),
            key=lambda section: (section.ordering, section.name),
        )
        for section in sorted_sections:
            bullets = [
                bullet_payloads[bullet_id]
                for bullet_id in section.bullet_ids
                if bullet_id in bullet_payloads
            ]
            section_payloads.append(
                PlaybookSectionRead(
                    name=section.name,
                    display_name=section.display_name,
                    description=section.description,
                    ordering=section.ordering,
                    metadata_=section.metadata,
                    bullets=bullets,
                )
            )

        return PlaybookSnapshotRead(sections=section_payloads, bullets=bullet_payloads)
