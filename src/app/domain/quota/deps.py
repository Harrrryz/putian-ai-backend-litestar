"""Dependency providers for quota domain."""

from __future__ import annotations

from app.domain.quota.services import UserUsageQuotaService
from app.lib.deps import create_service_provider

__all__ = ("provide_user_usage_quota_service",)

# User Usage Quota service provider
provide_user_usage_quota_service = create_service_provider(
    UserUsageQuotaService,
    error_messages={
        "duplicate_key": "Usage quota record with this user and month already exists.",
        "integrity": "Usage quota operation failed.",
    },
)
