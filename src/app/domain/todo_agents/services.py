"""Services for todo_agents domain."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Sequence
from uuid import UUID

from agents import Runner, SQLiteSession

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.todo.services import TagService, TodoService

from .tools.agent_factory import get_todo_agent
from .tools.tool_context import set_agent_context

__all__ = (
    "TodoAgentService",
    "create_todo_agent_service",
)

# Tools & agent implementation imported from todo_agent_tools.


class TodoAgentService:
    """Service class for managing todo agent interactions with SQLite session persistence.

    This class uses the official Agents SDK SQLiteSession for persistent conversation
    history, eliminating the need for manual session management.
    """

    def __init__(
        self,
        todo_service: "TodoService",
        tag_service: "TagService",
        session_db_path: str = "conversations.db",
    ) -> None:
        """Initialize the service with required dependencies.

        Args:
            todo_service: Service for todo operations
            tag_service: Service for tag operations
            session_db_path: Path to SQLite database for storing conversations
        """
        self.todo_service = todo_service
        self.tag_service = tag_service
        self.session_db_path = session_db_path
        self._sessions: dict[str, SQLiteSession] = {}

    async def chat_with_agent(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
    ) -> str:
        """Send a message to the todo agent and get a response with persistent conversation history.

        Args:
            user_id: ID of the user sending the message
            message: The message to send to the agent
            session_id: Optional session ID. If None, a new unique session ID will be generated

        Returns:
            The agent's response
        """
        # Generate unique session ID if not provided
        if session_id is None:
            session_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"

        # Ensure tools have service context for this user
        set_agent_context(self.todo_service, self.tag_service, UUID(user_id))

        # Get or create SQLite session
        if session_id not in self._sessions:
            self._sessions[session_id] = SQLiteSession(
                session_id, self.session_db_path)

        session = self._sessions[session_id]

        # Get the todo agent (with tools)
        agent = get_todo_agent()

        # Run the agent with session - conversation history is automatically managed!
        result = await Runner.run(agent, message, session=session)

        return result.final_output

    async def get_session_history(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a session.

        Args:
            session_id: The session ID to get history for
            limit: Maximum number of items to retrieve (None for all)

        Returns:
            List of conversation items in chronological order
        """
        if session_id not in self._sessions:
            # Return empty history if session doesn't exist
            return []

        session = self._sessions[session_id]
        items = await session.get_items(limit=limit)

        # Convert items to dict format for consistency
        return [dict(item) for item in items]

    async def clear_session_history(
        self,
        session_id: str,
    ) -> None:
        """Clear all messages from a session.

        Args:
            session_id: The session ID to clear
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            await session.clear_session()

    def list_active_sessions(self) -> list[str]:
        """List all active session IDs currently in memory.

        Returns:
            List of active session IDs
        """
        return list(self._sessions.keys())

    async def create_new_session(self, user_id: str) -> str:
        """Create a new session with a unique ID.

        Args:
            user_id: The user ID to create the session for

        Returns:
            The new session ID
        """
        session_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
        self._sessions[session_id] = SQLiteSession(
            session_id, self.session_db_path)
        return session_id


def create_todo_agent_service(
    todo_service: "TodoService",
    tag_service: "TagService",
    session_db_path: str = "conversations.db",
) -> TodoAgentService:
    """Factory function to create TodoAgentService with proper dependencies.

    Args:
        todo_service: Service for todo operations
        tag_service: Service for tag operations
        session_db_path: Path to SQLite database for storing conversations

    Returns:
        Configured TodoAgentService instance
    """
    return TodoAgentService(
        todo_service=todo_service,
        tag_service=tag_service,
        session_db_path=session_db_path,
    )
