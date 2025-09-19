"""User Account Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domain.accounts.services import UserService
from app.domain.accounts.services_email_verification import EmailVerificationService
from app.lib.deps import create_service_provider

if TYPE_CHECKING:
    from litestar import Request

# create a hard reference to this since it's used often
provide_users_service = create_service_provider(
    UserService,
    load=[
        selectinload(m.User.roles).options(
            joinedload(m.UserRole.role, innerjoin=True)),
        selectinload(m.User.oauth_accounts),
    ],
    error_messages={"duplicate_key": "This user already exists.",
                    "integrity": "User operation failed."},
)

provide_email_verification_service = create_service_provider(
    EmailVerificationService,
    load=[
        joinedload(m.EmailVerificationToken.user, innerjoin=True),
    ],
    error_messages={"duplicate_key": "Verification token already exists.",
                    "integrity": "Email verification operation failed."},
)


async def provide_user(request: Request[m.User, Any, Any]) -> m.User:
    """Get the user from the request.

    Args:
        request: current Request.

    Returns:
        User
    """
    return request.user
