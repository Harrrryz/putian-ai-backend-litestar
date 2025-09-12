"""Dependency providers for todo_agents domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.todo.services import TagService, TodoService
    from app.domain.todo_agents.services import TodoAgentService

from app.domain.todo_agents.services import TodoAgentService, create_todo_agent_service

__all__ = ("provide_todo_agent_service",)


async def provide_todo_agent_service(
    todo_service: "TodoService",
    tag_service: "TagService",
) -> "TodoAgentService":
    """Dependency provider for TodoAgentService.

    This function provides TodoAgentService instances to controllers
    through Litestar's dependency injection system.

    Args:
        todo_service: TodoService instance for todo operations
        tag_service: TagService instance for tag operations

    Returns:
        Configured TodoAgentService instance with SQLite session storage
    """
    return create_todo_agent_service(
        todo_service=todo_service,
        tag_service=tag_service,
    )
