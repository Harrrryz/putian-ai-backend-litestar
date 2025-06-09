from datetime import datetime
from uuid import UUID

from app.config.base import get_settings
from app.db.models.importance import Importance
from app.domain.accounts.schemas import PydanticBaseModel

__all__ = ("TodoModel",)

settings = get_settings()


class TodoModel(PydanticBaseModel):
    id: UUID
    item: str
    description: str | None = None
    created_time: datetime
    plan_time: datetime | None = None
    importance: Importance
    user_id: UUID
    tags: list[str] | None = None


class TodoCreate(PydanticBaseModel):
    item: str
    description: str | None = None
    plan_time: datetime | None = None
    importance: Importance = Importance.NONE
    tags: list[str] | None = None


class TodoUpdate(PydanticBaseModel):
    item: str | None = None
    description: str | None = None
    plan_time: datetime | None = None
    importance: Importance | None = None
    tags: list[str] | None = None


class TagModel(PydanticBaseModel):
    id: UUID
    name: str
    color: str | None = None
    user_id: UUID


class TagCreate(PydanticBaseModel):
    name: str
    color: str | None = None
    todo_id: UUID | None = None
