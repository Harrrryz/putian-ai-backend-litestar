"""Supporting tool implementations that are not CRUD or scheduling focused."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .argument_models import GetUserQuotaArgs
from .tool_context import get_current_user_id, get_quota_service, get_rate_limit_service

if TYPE_CHECKING:
    from agents import RunContextWrapper

__all__ = ["get_user_quota_impl"]


async def get_user_quota_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the get_user_quota function."""
    quota_service = get_quota_service()
    rate_limit_service = get_rate_limit_service()
    current_user_id = get_current_user_id()

    if not quota_service or not rate_limit_service or not current_user_id:
        return "Error: Agent context not properly initialized for quota information"

    try:
        parsed = GetUserQuotaArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"

    try:
        usage_stats = await rate_limit_service.get_user_usage_stats(
            user_id=current_user_id,
            quota_service=quota_service,
        )

        if parsed.include_details:
            reset_date_str = usage_stats.reset_date.strftime("%B %d, %Y")
            percentage_used = (usage_stats.usage_count / usage_stats.monthly_limit) * 100

            result = (
                f"📊 **Your Agent Usage Quota**\n\n"
                f"**Current Month:** {usage_stats.current_month}\n"
                f"**Used:** {usage_stats.usage_count}/{usage_stats.monthly_limit} requests ({percentage_used:.1f}%)\n"
                f"**Remaining:** {usage_stats.remaining_quota} requests\n"
                f"**Quota Resets:** {reset_date_str}\n\n"
            )

            if usage_stats.remaining_quota > 0:
                if percentage_used >= 80:
                    result += (
                        "⚠️ **Warning:** You're approaching your monthly limit. "
                        "Consider spacing out your requests."
                    )
                elif percentage_used >= 50:
                    result += "📈 **Notice:** You've used more than half of your monthly quota."
                else:
                    result += "✅ **Status:** You have plenty of quota remaining for this month."
            else:
                result += "🚫 **Limit Reached:** You have exceeded your monthly quota. Your quota will reset next month."
        else:
            result = (
                f"You have {usage_stats.remaining_quota} out of {usage_stats.monthly_limit} "
                "agent requests remaining this month."
            )

        return result

    except Exception as e:
        return f"Error retrieving quota information: {e!s}"
