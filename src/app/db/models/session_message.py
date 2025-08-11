from __future__ import annotations

import enum
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .agent_session import AgentSession


class MessageRole(enum.Enum):
    """Message roles based on OpenAI Agents SDK format."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SessionMessage(UUIDAuditBase):
    """Individual messages within agent conversation sessions."""

    __tablename__ = "session_message"
    __table_args__ = {"comment": "Messages in agent conversation sessions"}
    __pii_columns__ = {"content", "extra_data"}

    # Message content
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role_enum", native_enum=False),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional metadata for tool calls, function calls, etc.
    tool_call_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_data: Mapped[str | None] = mapped_column(
        Text, nullable=True)  # JSON string

    # Session relationship
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_session.id", ondelete="CASCADE"),
        nullable=False
    )

    # -----------
    # ORM Relationships
    # ------------

    session: Mapped[AgentSession] = relationship(
        back_populates="messages",
        lazy="joined"
    )
