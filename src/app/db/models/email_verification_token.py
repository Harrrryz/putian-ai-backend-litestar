"""Email verification token model."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .user import User


class EmailVerificationToken(UUIDAuditBase):
    """Email verification token for user signup."""

    __tablename__ = "email_verification_token"
    __table_args__ = {"comment": "Email verification tokens for user signup"}

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(length=64),
        nullable=False,
        unique=True,
        index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC) + timedelta(hours=24)
    )
    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        nullable=True, default=None)

    # -----------
    # ORM Relationships
    # ------------
    user: Mapped[User] = relationship(
        back_populates="verification_tokens",
        lazy="joined",
        innerjoin=True,
    )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not used and not expired)."""
        return not self.is_used and not self.is_expired
