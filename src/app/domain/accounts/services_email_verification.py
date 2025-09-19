"""Email verification service for managing verification tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from litestar.exceptions import NotFoundException, PermissionDeniedException

from app.db import models as m
from app.lib.email import generate_verification_token


class EmailVerificationService(SQLAlchemyAsyncRepositoryService[m.EmailVerificationToken]):
    """Handles database operations for email verification tokens."""

    class Repository(SQLAlchemyAsyncRepository[m.EmailVerificationToken]):
        """Email verification token SQLAlchemy Repository."""

        model_type = m.EmailVerificationToken

    repository_type = Repository

    async def create_verification_token(self, user_id: UUID) -> m.EmailVerificationToken:
        """Create a new verification token for a user.

        Args:
            user_id: The user's ID

        Returns:
            The created verification token
        """
        # Generate a new token
        token = generate_verification_token()

        # Create the verification token record
        token_data = {
            "user_id": user_id,
            "token": token,
        }

        return await self.create(token_data)

    async def verify_token(self, token: str) -> m.User:
        """Verify a token and mark the user as verified.

        Args:
            token: The verification token

        Returns:
            The verified user

        Raises:
            NotFoundException: If token doesn't exist
            PermissionDeniedException: If token is invalid, expired, or already used
        """
        # Find the verification token
        verification_token = await self.get_one_or_none(token=token)
        if verification_token is None:
            msg = "Verification token not found"
            raise NotFoundException(detail=msg)

        # Check if token is already used
        if verification_token.is_used:
            msg = "Verification token has already been used"
            raise PermissionDeniedException(detail=msg)

        # Check if token is expired
        if verification_token.is_expired:
            msg = "Verification token has expired"
            raise PermissionDeniedException(detail=msg)

        # Mark token as used
        await self.update(
            item_id=verification_token.id,
            data={
                "is_used": True,
                "used_at": datetime.now(UTC),
            }
        )

        # Load the user
        user = verification_token.user

        return user

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired verification tokens.

        Returns:
            Number of tokens deleted
        """
        # Find all expired tokens
        current_time = datetime.now(UTC)
        expired_tokens = await self.list(expires_at__lt=current_time)

        # Delete expired tokens
        count = 0
        for token in expired_tokens:
            await self.delete(token.id)
            count += 1

        return count

    async def get_user_pending_token(self, user_id: UUID) -> m.EmailVerificationToken | None:
        """Get the most recent pending verification token for a user.

        Args:
            user_id: The user's ID

        Returns:
            The most recent pending token, or None if none exists
        """
        tokens = await self.list(
            user_id=user_id,
            is_used=False,
        )

        # Sort by created_at descending (most recent first) and return the first non-expired token
        sorted_tokens = sorted(
            tokens, key=lambda t: t.created_at, reverse=True)
        for token in sorted_tokens:
            if not token.is_expired:
                return token

        return None
