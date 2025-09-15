"""Service for managing user usage quotas."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m

if TYPE_CHECKING:
    from datetime import datetime


class UserUsageQuotaService(SQLAlchemyAsyncRepositoryService[m.UserUsageQuota]):
    """Handles database operations for user usage quotas."""

    class Repository(SQLAlchemyAsyncRepository[m.UserUsageQuota]):
        """UserUsageQuota SQLAlchemy Repository."""

        model_type = m.UserUsageQuota

    repository_type = Repository
    match_fields = ["user_id", "month_year"]

    async def get_or_create_quota(
        self,
        user_id: UUID,
        month_year: str,
    ) -> m.UserUsageQuota:
        """Get existing quota record or create a new one for the user and month.

        Args:
            user_id: UUID of the user
            month_year: Month in YYYY-MM format

        Returns:
            UserUsageQuota record
        """
        existing_quota = await self.get_one_or_none(
            m.UserUsageQuota.user_id == str(user_id),
            m.UserUsageQuota.month_year == month_year,
        )

        if existing_quota:
            return existing_quota

        return await self.create({
            "user_id": str(user_id),
            "month_year": month_year,
            "usage_count": 0,
        })

    async def increment_usage(
        self,
        user_id: UUID,
        month_year: str,
    ) -> m.UserUsageQuota:
        """Increment the usage count for a user in a specific month.

        Args:
            user_id: UUID of the user
            month_year: Month in YYYY-MM format

        Returns:
            Updated UserUsageQuota record
        """
        quota = await self.get_or_create_quota(user_id, month_year)

        # Increment usage count using item_id and data parameters
        updated_quota = await self.update(
            item_id=quota.id,
            data={"usage_count": quota.usage_count + 1}
        )

        return updated_quota

    async def get_usage_count(
        self,
        user_id: UUID,
        month_year: str,
    ) -> int:
        """Get the current usage count for a user in a specific month.

        Args:
            user_id: UUID of the user
            month_year: Month in YYYY-MM format

        Returns:
            Current usage count (0 if no record exists)
        """
        quota = await self.get_one_or_none(
            m.UserUsageQuota.user_id == str(user_id),
            m.UserUsageQuota.month_year == month_year,
        )

        return quota.usage_count if quota else 0
