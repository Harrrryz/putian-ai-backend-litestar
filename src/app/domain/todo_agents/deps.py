"""Dependency providers for todo_agents domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.agent_sessions.services import AgentSessionService, SessionMessageService
    from app.domain.todo.services import TagService, TodoService
    from app.domain.todo_agents.services import TodoAgentService

from app.domain.todo_agents.services import TodoAgentService, create_todo_agent_service

__all__ = ("provide_todo_agent_service",)


async def provide_todo_agent_service(
    db_session: "AsyncSession",
    todo_service: "TodoService",
    tag_service: "TagService",
    agent_session_service: "AgentSessionService",
    message_service: "SessionMessageService",
) -> "TodoAgentService":
    """Dependency provider for TodoAgentService.

    This function provides TodoAgentService instances to controllers
    through Litestar's dependency injection system.

    Args:
        db_session: SQLAlchemy async session for database operations
        todo_service: TodoService instance for todo operations
        tag_service: TagService instance for tag operations
        agent_session_service: AgentSessionService for session management
        message_service: SessionMessageService for message management

    Returns:
        Configured TodoAgentService instance
    """
    return create_todo_agent_service(
        db_session=db_session,
        todo_service=todo_service,
        tag_service=tag_service,
        agent_session_service=agent_session_service,
        message_service=message_service,
    )
