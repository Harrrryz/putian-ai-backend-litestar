"""User usage quota model for rate limiting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .user import User


class UserUsageQuota(UUIDAuditBase):
    """Model for tracking monthly agent request usage per user."""

    __tablename__ = "user_usage_quota"
    __table_args__ = (
        UniqueConstraint("user_id", "month_year", name="uq_user_month"),
        Index("idx_user_usage_quota_user_month", "user_id", "month_year"),
        {"comment": "Monthly usage quota tracking for agent requests"},
    )

    # User reference
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Month tracking in YYYY-MM format
    month_year: Mapped[str] = mapped_column(
        String(7),  # YYYY-MM format
        nullable=False,
        comment="Month in YYYY-MM format",
    )

    # Usage count for the month
    usage_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of agent requests made in this month",
    )

    # Relationships
    user: Mapped[User] = relationship(
        back_populates="usage_quotas",
        lazy="select",
    )