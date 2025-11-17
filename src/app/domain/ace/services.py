"""Low-level services for ACE persistence models."""

from __future__ import annotations

from typing import Any

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m


class AcePlaybookSectionService(SQLAlchemyAsyncRepositoryService[m.AcePlaybookSection]):
    """Service wrapper for `AcePlaybookSection` operations."""

    class Repository(SQLAlchemyAsyncRepository[m.AcePlaybookSection]):
        model_type = m.AcePlaybookSection

    repository_type = Repository
    match_fields = ["name"]
    loader_options = [selectinload(m.AcePlaybookSection.bullets)]

    async def get_or_create(
        self,
        name: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> m.AcePlaybookSection:
        """Fetch an existing section or create a new ordered entry."""
        section = await self.get_one_or_none(m.AcePlaybookSection.name == name)
        if section:
            updates: dict[str, Any] = {}
            if display_name and section.display_name != display_name:
                updates["display_name"] = display_name
            if description and section.description != description:
                updates["description"] = description
            if metadata is not None:
                merged = dict(section.metadata_ or {})
                merged.update(metadata)
                if merged != section.metadata_:
                    updates["metadata_"] = merged
            if updates:
                section = await self.update(section.id, data=updates)
            return section

        ordering = await self._next_ordering()
        return await self.create(
            {
                "name": name,
                "display_name": display_name or name.title(),
                "description": description,
                "ordering": ordering,
                "metadata_": metadata or {},
            },
            auto_commit=False,
        )

    async def _next_ordering(self) -> int:
        stmt = select(func.max(m.AcePlaybookSection.ordering))
        result = await self.repository.session.execute(stmt)  # type: ignore[attr-defined]
        current = result.scalar_one_or_none() or 0
        return current + 1


class AcePlaybookBulletService(SQLAlchemyAsyncRepositoryService[m.AcePlaybookBullet]):
    """Service wrapper for `AcePlaybookBullet` operations."""

    class Repository(SQLAlchemyAsyncRepository[m.AcePlaybookBullet]):
        model_type = m.AcePlaybookBullet

    repository_type = Repository
    match_fields = ["bullet_id"]
    loader_options = [joinedload(m.AcePlaybookBullet.section)]


class AcePlaybookRevisionService(SQLAlchemyAsyncRepositoryService[m.AcePlaybookRevision]):
    """Service wrapper for playbook revision audit logs."""

    class Repository(SQLAlchemyAsyncRepository[m.AcePlaybookRevision]):
        model_type = m.AcePlaybookRevision

    repository_type = Repository
    loader_options = []


__all__ = (
    "AcePlaybookBulletService",
    "AcePlaybookRevisionService",
    "AcePlaybookSectionService",
)
