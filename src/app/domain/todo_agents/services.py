"""Services for todo_agents domain."""

from __future__ import annotations

# (Removed unused datetime imports)
from typing import TYPE_CHECKING, Any
from uuid import UUID

from agents import Runner

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.agent_sessions.services import AgentSessionService, SessionMessageService
    from app.domain.todo.services import TagService, TodoService

from .tools.agent_factory import get_todo_agent
from .tools.system_instructions import TODO_SYSTEM_INSTRUCTIONS
from .tools.tool_context import set_agent_context

__all__ = (
    "TodoAgentService",
    "create_todo_agent_service",
)

# Tools & agent implementation imported from todo_agent_tools.


class TodoAgentService:
    """Service class for managing todo agent interactions with session persistence.

    This class integrates with the existing agent_sessions domain to provide
    persistent conversation history for todo management agents.
    """

    def __init__(
        self,
        db_session: "AsyncSession",
        todo_service: "TodoService",
        tag_service: "TagService",
        agent_session_service: "AgentSessionService",
        message_service: "SessionMessageService",
    ) -> None:
        """Initialize the service with required dependencies."""
        self.db_session = db_session
        self.todo_service = todo_service
        self.tag_service = tag_service
        self.agent_session_service = agent_session_service
        self.message_service = message_service

    async def chat_with_agent(
        self,
        session_id: str,
        user_id: str,
        message: str,
        session_name: str | None = None,
    ) -> str:
        """Send a message to the todo agent and get a response with persistent conversation history."""
        # Ensure tools have service context for this user
        set_agent_context(self.todo_service, self.tag_service, UUID(user_id))

        # Create or get existing session using agent sessions service
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))

        if not session:
            session_data = {
                "session_id": session_id,
                "session_name": session_name or "Todo Management Chat",
                "user_id": UUID(user_id),
                "agent_name": "TodoAssistant",
                "agent_instructions": TODO_SYSTEM_INSTRUCTIONS,
                "is_active": True,
            }
            session = await self.agent_session_service.create(session_data)

        # Store user message in the session
        from app.db.models.session_message import MessageRole

        user_message_data = {
            "session_id": session.id,
            "role": MessageRole.USER,
            "content": message,
            "tool_call_id": None,
            "tool_name": None,
            "extra_data": None,
        }
        await self.message_service.create(user_message_data)

        # Get the todo agent (with tools)
        agent = get_todo_agent()

        # Run the agent to get response
        result = await Runner.run(agent, message)
        response_content = result.final_output
        print("Response:", result.to_input_list())

        # Store assistant response in the session
        assistant_message_data = {
            "session_id": session.id,
            "role": MessageRole.ASSISTANT,
            "content": response_content,
            "tool_call_id": None,
            "tool_name": None,
            "extra_data": None,
        }
        await self.message_service.create(assistant_message_data)

        return response_content

    async def get_session_history(
        self,
        session_id: str,
        user_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a session."""
        # Get session using agent sessions service
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))
        if not session:
            return []

        # Get messages from the session
        messages = await self.message_service.get_recent_messages(session.id, limit or 50)

        # Convert to OpenAI format
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]

    async def clear_session_history(
        self,
        session_id: str,
        user_id: str,
    ) -> None:
        """Clear all messages from a session."""
        # Get session using agent sessions service
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))
        if session:
            await self.message_service.clear_session_messages(session.id)

    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List all agent sessions for a user."""
        # Get sessions from the agent session service
        sessions = await self.agent_session_service.list(
            self.agent_session_service.model_type.user_id == UUID(user_id)
        )
        return [
            {
                "session_id": session.session_id,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "is_active": session.is_active,
            }
            for session in sessions
        ]


def create_todo_agent_service(
    db_session: "AsyncSession",
    todo_service: "TodoService",
    tag_service: "TagService",
    agent_session_service: "AgentSessionService",
    message_service: "SessionMessageService",
) -> TodoAgentService:
    """Factory function to create TodoAgentService with proper dependencies."""
    return TodoAgentService(
        db_session=db_session,
        todo_service=todo_service,
        tag_service=tag_service,
        agent_session_service=agent_session_service,
        message_service=message_service,
    )
