"""Controllers for todo_agents domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import structlog
from litestar import Controller, delete, get, post
from litestar.di import Provide
from litestar.params import Dependency

if TYPE_CHECKING:
    import app.db.models as m
    from app.domain.quota.services import UserUsageQuotaService
    from app.domain.todo_agents.services import TodoAgentService
    from app.lib.rate_limit_service import RateLimitService
    from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.todo.deps import provide_tag_service, provide_todo_service
from app.domain.todo_agents import urls
from app.domain.todo_agents.deps import provide_rate_limit_service, provide_todo_agent_service, provide_user_usage_quota_service
from app.domain.todo_agents.schemas import (
    AgentTodoRequest,
    AgentTodoResponse,
    RateLimitErrorResponse,
    UsageStatsResponse,
)
from app.lib.exceptions import RateLimitExceededException
from app.lib.rate_limit_service import RateLimitService

logger = structlog.get_logger()

__all__ = ("TodoAgentController",)


class TodoAgentController(Controller):
    """Controller for AI agent todo operations."""

    tags = ["Todo Agents"]
    path = urls.TODO_AGENTS_BASE

    dependencies = {
        "todo_service": Provide(provide_todo_service),
        "tag_service": Provide(provide_tag_service),
        "rate_limit_service": Provide(provide_rate_limit_service),
        "quota_service": Provide(provide_user_usage_quota_service),
        "todo_agent_service": Provide(provide_todo_agent_service),
    }

    @post(path="/agent-create", operation_id="agent_create_todo")
    async def agent_create_todo(
        self,
        current_user: m.User,
        data: AgentTodoRequest,
        todo_agent_service: Annotated["TodoAgentService", Dependency(skip_validation=True)],
    ) -> AgentTodoResponse | RateLimitErrorResponse:
        """Create a todo using AI agent with persistent conversation sessions."""
        try:
            # Generate session ID if not provided
            session_id = data.session_id or f"user_{current_user.id}_todo_agent"

            # Extract the user message from the messages list
            if not data.messages:
                return AgentTodoResponse(
                    status="error",
                    message="No messages provided",
                    agent_response=[]
                )

            # Get the last user message
            user_message = ""
            for msg in reversed(data.messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

            if not user_message:
                return AgentTodoResponse(
                    status="error",
                    message="No user message found in messages",
                    agent_response=[]
                )

            # Use the session-based agent to process the message with rate limiting
            response = await todo_agent_service.chat_with_agent(
                user_id=str(current_user.id),
                message=user_message,
                session_id=session_id,
            )

            # Get the conversation history to return as agent_response
            conversation_history = await todo_agent_service.get_session_history(
                session_id=session_id,
                limit=10  # Return last 10 messages
            )

            return AgentTodoResponse(
                status="success",
                message=response,
                agent_response=conversation_history
            )

        except RateLimitExceededException as e:
            logger.warning("Rate limit exceeded",
                           user_id=current_user.id,
                           current_usage=e.current_usage,
                           monthly_limit=e.monthly_limit)
            return RateLimitErrorResponse(
                message=e.detail,
                current_usage=e.current_usage,
                monthly_limit=e.monthly_limit,
                reset_date=e.reset_date,
                remaining_quota=max(0, e.monthly_limit - e.current_usage),
            )
        except Exception as e:
            logger.exception("Agent todo creation failed",
                             error=str(e), user_id=current_user.id)
            return AgentTodoResponse(
                status="error",
                message=f"Failed to process todo with AI agent: {e!s}",
                agent_response=[]
            )

    @get(path="/agent-sessions", operation_id="list_agent_sessions")
    async def list_agent_sessions(
        self,
        current_user: m.User,
        todo_agent_service: Annotated["TodoAgentService", Dependency(skip_validation=True)],
    ) -> dict[str, Any]:
        """List all active agent sessions."""
        try:
            sessions = todo_agent_service.list_active_sessions()
            # Filter sessions for this user (basic filtering by session ID pattern)
            user_sessions = [
                session_id for session_id in sessions
                if session_id.startswith(f"user_{current_user.id}_")
            ]
        except Exception as e:
            logger.exception("Failed to list agent sessions",
                             error=str(e), user_id=current_user.id)
            return {
                "status": "error",
                "message": f"Failed to list agent sessions: {e!s}",
                "sessions": []
            }
        else:
            return {
                "status": "success",
                "sessions": user_sessions
            }

    @post(path="/agent-sessions/new", operation_id="create_new_session")
    async def create_new_session(
        self,
        current_user: m.User,
        todo_agent_service: Annotated["TodoAgentService", Dependency(skip_validation=True)],
    ) -> dict[str, Any]:
        """Create a new agent session with a unique ID."""
        try:
            session_id = await todo_agent_service.create_new_session(str(current_user.id))
        except Exception as e:
            logger.exception("Failed to create new session",
                             error=str(e), user_id=current_user.id)
            return {
                "status": "error",
                "message": f"Failed to create new session: {e!s}",
                "session_id": None
            }
        else:
            return {
                "status": "success",
                "message": "New session created successfully",
                "session_id": session_id
            }

    @get(path="/agent-sessions/{session_id:str}/history", operation_id="get_session_history")
    async def get_session_history(
        self,
        session_id: str,
        current_user: m.User,
        todo_agent_service: Annotated["TodoAgentService", Dependency(skip_validation=True)],
        limit: int = 50
    ) -> dict[str, Any]:
        """Get conversation history for a specific session."""
        try:
            history = await todo_agent_service.get_session_history(
                session_id=session_id,
                limit=limit
            )
        except Exception as e:
            logger.exception("Failed to get session history",
                             error=str(e), user_id=current_user.id, session_id=session_id)
            return {
                "status": "error",
                "message": f"Failed to get session history: {e!s}",
                "history": []
            }
        else:
            return {
                "status": "success",
                "session_id": session_id,
                "history": history
            }

    @delete(path="/agent-sessions/{session_id:str}", operation_id="clear_session_history", status_code=200)
    async def clear_session_history(
        self,
        session_id: str,
        current_user: m.User,
        todo_agent_service: Annotated["TodoAgentService", Dependency(skip_validation=True)],
    ) -> dict[str, Any]:
        """Clear conversation history for a specific session."""
        try:
            await todo_agent_service.clear_session_history(
                session_id=session_id
            )
        except Exception as e:
            logger.exception("Failed to clear session history",
                             error=str(e), user_id=current_user.id, session_id=session_id)
            return {
                "status": "error",
                "message": f"Failed to clear session history: {e!s}"
            }
        else:
            return {
                "status": "success",
                "message": f"Session {session_id} history cleared successfully"
            }

    @get(path="/usage-stats", operation_id="get_usage_stats")
    async def get_usage_stats(
        self,
        current_user: m.User,
        rate_limit_service: Annotated["RateLimitService", Dependency(skip_validation=True)],
        quota_service: Annotated["UserUsageQuotaService", Dependency(skip_validation=True)],
    ) -> UsageStatsResponse:
        """Get current usage statistics for the user."""
        try:
            stats = await rate_limit_service.get_user_usage_stats(
                user_id=current_user.id,
                quota_service=quota_service
            )

            return UsageStatsResponse(
                current_month=stats.current_month,
                usage_count=stats.usage_count,
                monthly_limit=stats.monthly_limit,
                remaining_quota=stats.remaining_quota,
                reset_date=stats.reset_date,
            )
        except Exception as e:
            logger.exception("Failed to get usage stats",
                             error=str(e), user_id=current_user.id)
            # Return default stats in case of error
            from datetime import datetime, timezone
            return UsageStatsResponse(
                current_month=datetime.now(timezone.utc).strftime("%Y-%m"),
                usage_count=0,
                monthly_limit=200,
                remaining_quota=200,
                reset_date=datetime.now(timezone.utc).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0),
            )
