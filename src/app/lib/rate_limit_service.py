"""Rate limiting service for agent requests."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

if TYPE_CHECKING:
    from app.domain.quota.services import UserUsageQuotaService

from app.lib.exceptions import RateLimitExceededException

__all__ = (
    "RateLimitService",
    "UsageStats",
)

DEFAULT_MONTHLY_LIMIT = 200


class UsageStats(NamedTuple):
    """Usage statistics for a user."""

    current_month: str
    usage_count: int
    monthly_limit: int
    remaining_quota: int
    reset_date: datetime


class RateLimitService:
    """Service for managing rate limiting of agent requests."""

    def __init__(self, monthly_limit: int = DEFAULT_MONTHLY_LIMIT) -> None:
        """Initialize the rate limit service.

        Args:
            monthly_limit: Maximum number of agent requests per user per month
        """
        self.monthly_limit = monthly_limit

    async def check_and_increment_usage(
        self,
        user_id: UUID,
        quota_service: "UserUsageQuotaService",
    ) -> None:
        """Check rate limit and increment usage if within limits.

        Args:
            user_id: UUID of the user making the request
            quota_service: UserUsageQuotaService for database operations

        Raises:
            RateLimitExceededException: If user has exceeded their monthly quota
        """
        current_month = self._get_current_month()

        # Get current usage count
        current_usage = await quota_service.get_usage_count(user_id, current_month)

        # Check if user has exceeded limit
        if current_usage >= self.monthly_limit:
            reset_date = self._get_reset_date(current_month)
            raise RateLimitExceededException(
                user_id=user_id,
                current_usage=current_usage,
                monthly_limit=self.monthly_limit,
                reset_date=reset_date,
            )

        # Increment usage count
        await quota_service.increment_usage(user_id, current_month)

    async def get_user_usage_stats(
        self,
        user_id: UUID,
        quota_service: "UserUsageQuotaService",
    ) -> UsageStats:
        """Get current usage statistics for a user.

        Args:
            user_id: UUID of the user
            quota_service: UserUsageQuotaService for database operations

        Returns:
            UsageStats object with current usage information
        """
        current_month = self._get_current_month()

        # Get usage count for current month
        usage_count = await quota_service.get_usage_count(user_id, current_month)

        remaining_quota = max(0, self.monthly_limit - usage_count)
        reset_date = self._get_reset_date(current_month)

        return UsageStats(
            current_month=current_month,
            usage_count=usage_count,
            monthly_limit=self.monthly_limit,
            remaining_quota=remaining_quota,
            reset_date=reset_date,
        )

    async def get_remaining_quota(
        self,
        user_id: UUID,
        quota_service: "UserUsageQuotaService",
    ) -> int:
        """Get remaining quota for current month.

        Args:
            user_id: UUID of the user
            quota_service: UserUsageQuotaService for database operations

        Returns:
            Number of requests remaining this month
        """
        stats = await self.get_user_usage_stats(user_id, quota_service)
        return stats.remaining_quota

    def _get_current_month(self) -> str:
        """Get current month in YYYY-MM format.

        Returns:
            Current month as string in YYYY-MM format
        """
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m")

    def _get_reset_date(self, month_year: str) -> datetime:
        """Get the reset date for a given month (first day of next month).

        Args:
            month_year: Month in YYYY-MM format

        Returns:
            Datetime object representing when the quota resets
        """
        year, month = map(int, month_year.split("-"))

        # Calculate next month
        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1

        return datetime(next_year, next_month, 1, tzinfo=timezone.utc)
