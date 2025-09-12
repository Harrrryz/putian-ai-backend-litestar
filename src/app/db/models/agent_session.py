from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .session_message import SessionMessage
    from .user import User


class AgentSession(UUIDAuditBase):
    """Agent conversation sessions for OpenAI Agents SDK integration."""

    __tablename__ = "agent_session"
    __table_args__ = {"comment": "Agent conversation sessions"}
    __pii_columns__ = {"session_name", "session_id"}

    # Session identification
    session_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True)
    session_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Session state
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)

    # User ownership
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False
    )

    # Agent configuration (optional metadata)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -----------
    # ORM Relationships
    # ------------

    user: Mapped[User] = relationship(
        back_populates="agent_sessions",
        lazy="joined"
    )

    messages: Mapped[list[SessionMessage]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="SessionMessage.created_at"
    )
