from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.repository import (
    SQLAlchemyAsyncRepository,
)
from advanced_alchemy.service import (
    SQLAlchemyAsyncRepositoryService,
)

from app.db import models as m

if TYPE_CHECKING:
    from datetime import datetime


class TodoService(SQLAlchemyAsyncRepositoryService[m.Todo]):
    """Handles database operations for todo."""

    class Repository(SQLAlchemyAsyncRepository[m.Todo]):
        """Todo SQLAlchemy Repository."""

        model_type = m.Todo

    repository_type = Repository
    match_fields = ["item"]

    async def get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> m.Todo | None:
        """Get a todo item by ID for the specified user."""
        todo = await self.get_one_or_none(m.Todo.id == todo_id, m.Todo.user_id == user_id)
        if not todo:
            return None
        return todo

    async def check_time_conflict(
        self,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_todo_id: UUID | None = None
    ) -> list[m.Todo]:
        """Check for time conflicts with existing todos for a user.

        Args:
            user_id: The user's UUID
            start_time: The start time to check for conflicts
            end_time: The end time to check for conflicts
            exclude_todo_id: Optional todo ID to exclude from conflict checking (for updates)

        Returns:
            List of conflicting Todo objects, empty if no conflicts
        """
        # Two time ranges overlap if:
        # 1. The new start_time is before existing end_time AND
        # 2. The new end_time is after existing start_time
        filters = [
            m.Todo.user_id == user_id,
            m.Todo.start_time < end_time,  # existing start is before new end
            m.Todo.end_time > start_time,  # existing end is after new start
        ]

        # Exclude the current todo if updating
        if exclude_todo_id:
            filters.append(m.Todo.id != exclude_todo_id)

        conflicts, _ = await self.list_and_count(*filters)
        return list(conflicts)


class TagService(SQLAlchemyAsyncRepositoryService[m.Tag]):
    """Handles database operations for tags."""

    class TagRepository(SQLAlchemyAsyncRepository[m.Tag]):
        """Tag SQLAlchemy Repository."""

        model_type = m.Tag

    repository_type = TagRepository
    match_fields = ["name"]

    async def get_or_create_tag(self, user_id: UUID, name: str, color: str | None = None) -> m.Tag:
        """Get existing tag or create a new one for the user."""
        existing_tag = await self.get_one_or_none(m.Tag.user_id == user_id, m.Tag.name == name)

        if existing_tag:
            return existing_tag

        return await self.create({"name": name, "color": color, "user_id": user_id})
