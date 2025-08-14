"""Services for agent_sessions domain."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m

if TYPE_CHECKING:
    from collections.abc import Sequence


class AgentSessionService(SQLAlchemyAsyncRepositoryService[m.AgentSession]):
    """Handles database operations for agent sessions."""

    class Repository(SQLAlchemyAsyncRepository[m.AgentSession]):
        """Agent Session SQLAlchemy Repository."""

        model_type = m.AgentSession

    repository_type = Repository
    # Prevent duplicate session_id per user
    match_fields = ["session_id", "user_id"]

    async def get_by_user(self, user_id: UUID) -> Sequence[m.AgentSession]:
        """Get all agent sessions for a specific user."""
        sessions, _ = await self.list_and_count(m.AgentSession.user_id == user_id)
        return sessions

    async def get_by_session_id(self, session_id: str, user_id: UUID) -> m.AgentSession | None:
        """Get an agent session by session_id for the specified user."""
        return await self.get_one_or_none(
            m.AgentSession.session_id == session_id,
            m.AgentSession.user_id == user_id
        )

    async def get_active_sessions(self, user_id: UUID) -> Sequence[m.AgentSession]:
        """Get all active agent sessions for a specific user."""
        sessions, _ = await self.list_and_count(
            m.AgentSession.user_id == user_id,
            m.AgentSession.is_active == True  # noqa: E712
        )
        return sessions

    async def deactivate_session(self, session_id: UUID, user_id: UUID) -> m.AgentSession | None:
        """Deactivate an agent session."""
        session = await self.get_one_or_none(
            m.AgentSession.id == session_id,
            m.AgentSession.user_id == user_id
        )
        if session:
            return await self.update(
                data={"is_active": False},
                item_id=session_id
            )
        return None

    async def activate_session(self, session_id: UUID, user_id: UUID) -> m.AgentSession | None:
        """Activate an agent session."""
        session = await self.get_one_or_none(
            m.AgentSession.id == session_id,
            m.AgentSession.user_id == user_id
        )
        if session:
            return await self.update(
                data={"is_active": True},
                item_id=session_id
            )
        return None


class SessionMessageService(SQLAlchemyAsyncRepositoryService[m.SessionMessage]):
    """Handles database operations for session messages."""

    class Repository(SQLAlchemyAsyncRepository[m.SessionMessage]):
        """Session Message SQLAlchemy Repository."""

        model_type = m.SessionMessage

    repository_type = Repository
    match_fields = []  # No unique constraints for messages

    async def get_by_session(self, session_id: UUID) -> Sequence[m.SessionMessage]:
        """Get all messages for a specific session."""
        messages, _ = await self.list_and_count(
            m.SessionMessage.session_id == session_id
        )
        return messages

    async def get_session_message_count(self, session_id: UUID) -> int:
        """Get the total number of messages in a session."""
        _, count = await self.list_and_count(m.SessionMessage.session_id == session_id)
        return count

    async def clear_session_messages(self, session_id: UUID) -> int:
        """Clear all messages from a session."""
        messages, _ = await self.list_and_count(m.SessionMessage.session_id == session_id)
        deleted_count = 0
        for message in messages:
            await self.delete(message.id)
            deleted_count += 1
        return deleted_count

    async def get_recent_messages(self, session_id: UUID, limit: int = 10) -> Sequence[m.SessionMessage]:
        """Get the most recent messages from a session."""
        messages, _ = await self.list_and_count(
            m.SessionMessage.session_id == session_id
        )
        # Sort by created_at in descending order and limit, then reverse for chronological order
        sorted_messages = sorted(
            messages, key=lambda x: x.created_at, reverse=True)[:limit]
        return list(reversed(sorted_messages))
