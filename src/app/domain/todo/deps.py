"""Todo Controllers."""

from __future__ import annotations

from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domain.todo.services import TagService, TodoService
from app.lib.deps import create_service_provider

# create a hard reference to this since it's used oven
provide_todo_service = create_service_provider(
    TodoService,
    load=[
        selectinload(m.Todo.todo_tags).options(
            joinedload(m.TodoTag.tag, innerjoin=True)),
        joinedload(m.Todo.user, innerjoin=True),
    ],
    error_messages={"duplicate_key": "This user already exists.",
                    "integrity": "User operation failed."},
)

provide_tag_service = create_service_provider(
    TagService,
    load=[
        selectinload(m.Tag.tag_todos).options(
            joinedload(m.TodoTag.todo, innerjoin=True)),
        joinedload(m.Tag.user, innerjoin=True),
    ],
    error_messages={"duplicate_key": "This tag already exists.",
                    "integrity": "Tag operation failed."},
)
