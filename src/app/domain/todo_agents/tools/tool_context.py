"""Context management for todo agent tools.

This module manages the global context (services and user information)
that tool implementations need to access during execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from app.domain.todo.services import TagService, TodoService

__all__ = ["get_current_user_id", "get_tag_service",
           "get_todo_service", "set_agent_context"]

# Global context variables (set per user/session)
_todo_service: TodoService | None = None
_tag_service: TagService | None = None
_current_user_id: UUID | None = None


def set_agent_context(todo_service: TodoService, tag_service: TagService, user_id: UUID) -> None:
    """Inject services & user context for subsequent tool calls."""
    global _todo_service, _tag_service, _current_user_id  # noqa: PLW0603
    _todo_service = todo_service
    _tag_service = tag_service
    _current_user_id = user_id


def get_todo_service() -> TodoService | None:
    """Get the current todo service instance."""
    return _todo_service


def get_tag_service() -> TagService | None:
    """Get the current tag service instance."""
    return _tag_service


def get_current_user_id() -> UUID | None:
    """Get the current user ID."""
    return _current_user_id
