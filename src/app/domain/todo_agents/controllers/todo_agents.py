"""Controllers for todo_agents domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import structlog
from litestar import Controller, delete, get, post
from litestar.di import Provide
from litestar.params import Dependency

if TYPE_CHECKING:
    import app.db.models as m
    from app.domain.todo_agents.services import TodoAgentService
from app.domain.todo.deps import provide_tag_service, provide_todo_service
from app.domain.todo_agents import urls
from app.domain.todo_agents.deps import provide_todo_agent_service
from app.domain.todo_agents.schemas import AgentTodoRequest, AgentTodoResponse

logger = structlog.get_logger()

__all__ = ("TodoAgentController",)


class TodoAgentController(Controller):
    """Controller for AI agent todo operations."""

    tags = ["Todo Agents"]
    path = urls.TODO_AGENTS_BASE

    dependencies = {
        "todo_service": Provide(provide_todo_service),
        "tag_service": Provide(provide_tag_service),
        "todo_agent_service": Provide(provide_todo_agent_service),
    }

    @post(path="/agent-create", operation_id="agent_create_todo")
    async def agent_create_todo(
        self,
        current_user: m.User,
        data: AgentTodoRequest,
        todo_agent_service: Annotated["TodoAgentService", Dependency(skip_validation=True)],
    ) -> AgentTodoResponse:
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

            # Use the session-based agent to process the message
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
