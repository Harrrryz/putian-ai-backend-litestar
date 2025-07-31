from __future__ import annotations

from uuid import UUID  # noqa: TC003

from advanced_alchemy.repository import (
    SQLAlchemyAsyncRepository,
)
from advanced_alchemy.service import (
    SQLAlchemyAsyncRepositoryService,
)

from app.db import models as m
from sqlalchemy import select
from typing import List


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
