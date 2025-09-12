"""Custom session implementation for OpenAI Agents SDK integration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import AgentSession, MessageRole, SessionMessage


class DatabaseSession:
    """Custom session implementation following the OpenAI Agents SDK Session protocol.

    This implementation stores conversation history in the database using the
    AgentSession and SessionMessage models.
    """

    def __init__(
        self,
        session_id: str,
        user_id: str,
        db_session: AsyncSession,
        agent_name: str | None = None,
        agent_instructions: str | None = None,
        session_name: str | None = None,
    ) -> None:
        """Initialize the database session.

        Args:
            session_id: Unique identifier for the conversation session
            user_id: ID of the user who owns this session
            db_session: SQLAlchemy async session for database operations
            agent_name: Optional name of the agent
            agent_instructions: Optional agent instructions
            session_name: Optional human-readable session name
        """
        self.session_id = session_id
        self.user_id = user_id
        self.db_session = db_session
        self.agent_name = agent_name
        self.agent_instructions = agent_instructions
        self.session_name = session_name
        self._agent_session: AgentSession | None = None

    async def _get_or_create_agent_session(self) -> AgentSession:
        """Get or create the AgentSession record."""
        if self._agent_session is not None:
            return self._agent_session

        # Try to find existing session
        stmt = (
            select(AgentSession)
            .options(selectinload(AgentSession.messages))
            .where(
                AgentSession.session_id == self.session_id,
                AgentSession.user_id == self.user_id,
            )
        )
        result = await self.db_session.execute(stmt)
        agent_session = result.scalar_one_or_none()

        if agent_session is None:
            # Create new session
            agent_session = AgentSession(
                session_id=self.session_id,
                user_id=self.user_id,
                agent_name=self.agent_name,
                agent_instructions=self.agent_instructions,
                session_name=self.session_name,
            )
            self.db_session.add(agent_session)
            await self.db_session.commit()
            await self.db_session.refresh(agent_session)

        self._agent_session = agent_session
        return agent_session

    async def get_items(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Retrieve conversation history for this session.

        Args:
            limit: Maximum number of items to retrieve (None for all)

        Returns:
            List of message dictionaries in OpenAI Agents SDK format
        """
        agent_session = await self._get_or_create_agent_session()

        # Get messages ordered by creation time
        stmt = (
            select(SessionMessage)
            .where(SessionMessage.session_id == agent_session.id)
            .order_by(SessionMessage.created_at)
        )

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.db_session.execute(stmt)
        messages = result.scalars().all()

        # Convert to OpenAI format
        items = []
        for message in messages:
            item = {
                "role": message.role.value,
                "content": message.content,
            }

            # Add tool call information if present
            if message.tool_call_id:
                item["tool_call_id"] = message.tool_call_id
            if message.tool_name:
                item["tool_name"] = message.tool_name
            if message.extra_data:
                try:
                    metadata = json.loads(message.extra_data)
                    item.update(metadata)
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON

            items.append(item)

        return items

    async def add_items(self, items: list[dict[str, Any]]) -> None:
        """Store new items for this session.

        Args:
            items: List of message dictionaries to add
        """
        agent_session = await self._get_or_create_agent_session()

        for item in items:
            # Extract role and content
            role_str = item.get("role", "user")
            content = item.get("content", "")

            # Map role string to enum
            try:
                role = MessageRole(role_str)
            except ValueError:
                # Default to user if role is unknown
                role = MessageRole.USER

            # Extract optional fields
            tool_call_id = item.get("tool_call_id")
            tool_name = item.get("tool_name")

            # Store additional metadata as JSON
            metadata = {
                key: value
                for key, value in item.items()
                if key not in ("role", "content", "tool_call_id", "tool_name")
            }

            metadata_json = json.dumps(metadata) if metadata else None

            # Create message record
            message = SessionMessage(
                session_id=agent_session.id,
                role=role,
                content=content,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                extra_data=metadata_json,
            )

            self.db_session.add(message)

        await self.db_session.commit()

    async def pop_item(self) -> dict[str, Any] | None:
        """Remove and return the most recent item from this session.

        Returns:
            The removed message dictionary, or None if session is empty
        """
        agent_session = await self._get_or_create_agent_session()

        # Get the most recent message
        stmt = (
            select(SessionMessage)
            .where(SessionMessage.session_id == agent_session.id)
            .order_by(SessionMessage.created_at.desc())
            .limit(1)
        )

        result = await self.db_session.execute(stmt)
        message = result.scalar_one_or_none()

        if message is None:
            return None

        # Convert to OpenAI format
        item = {
            "role": message.role.value,
            "content": message.content,
        }

        if message.tool_call_id:
            item["tool_call_id"] = message.tool_call_id
        if message.tool_name:
            item["tool_name"] = message.tool_name
        if message.extra_data:
            try:
                metadata = json.loads(message.extra_data)
                item.update(metadata)
            except json.JSONDecodeError:
                pass

        # Delete the message
        await self.db_session.delete(message)
        await self.db_session.commit()

        return item

    async def clear_session(self) -> None:
        """Clear all items for this session."""
        agent_session = await self._get_or_create_agent_session()

        # Delete all messages in this session
        stmt = select(SessionMessage).where(
            SessionMessage.session_id == agent_session.id)
        result = await self.db_session.execute(stmt)
        messages = result.scalars().all()

        for message in messages:
            await self.db_session.delete(message)

        await self.db_session.commit()

    async def update_session_metadata(
        self,
        session_name: str | None = None,
        agent_name: str | None = None,
        agent_instructions: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        """Update session metadata.

        Args:
            session_name: New session name
            agent_name: New agent name
            agent_instructions: New agent instructions
            is_active: New active status
        """
        agent_session = await self._get_or_create_agent_session()

        if session_name is not None:
            agent_session.session_name = session_name
        if agent_name is not None:
            agent_session.agent_name = agent_name
        if agent_instructions is not None:
            agent_session.agent_instructions = agent_instructions
        if is_active is not None:
            agent_session.is_active = is_active

        await self.db_session.commit()
