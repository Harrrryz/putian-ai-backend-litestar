"""Password reset service for managing password reset tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from litestar.exceptions import NotFoundException, PermissionDeniedException

from app.db import models as m
from app.lib.email import generate_verification_token


class PasswordResetService(SQLAlchemyAsyncRepositoryService[m.PasswordResetToken]):
    """Handles database operations for password reset tokens."""

    class Repository(SQLAlchemyAsyncRepository[m.PasswordResetToken]):
        """Password reset token SQLAlchemy Repository."""

        model_type = m.PasswordResetToken

    repository_type = Repository

    async def create_password_reset_token(self, user_id: UUID) -> m.PasswordResetToken:
        """Create a new password reset token for a user.

        Args:
            user_id: The user's ID

        Returns:
            The created password reset token
        """
        # Generate a new token
        token = generate_verification_token()

        # Create the password reset token record
        token_data = {
            "user_id": user_id,
            "token": token,
        }

        return await self.create(token_data)

    async def verify_token(self, token: str) -> m.User:
        """Verify a token and return the associated user.

        Args:
            token: The password reset token

        Returns:
            The user associated with the token

        Raises:
            NotFoundException: If token doesn't exist
            PermissionDeniedException: If token is invalid, expired, or already used
        """
        # Find the password reset token
        reset_token = await self.get_one_or_none(token=token)
        if reset_token is None:
            msg = "Password reset token not found"
            raise NotFoundException(detail=msg)

        # Check if token is already used
        if reset_token.is_used:
            msg = "Password reset token has already been used"
            raise PermissionDeniedException(detail=msg)

        # Check if token is expired
        if reset_token.is_expired:
            msg = "Password reset token has expired"
            raise PermissionDeniedException(detail=msg)

        # Load the user
        user = reset_token.user

        return user

    async def use_token(self, token: str) -> m.User:
        """Mark a token as used and return the associated user.

        Args:
            token: The password reset token

        Returns:
            The user associated with the token

        Raises:
            NotFoundException: If token doesn't exist
            PermissionDeniedException: If token is invalid, expired, or already used
        """
        # Find the password reset token
        reset_token = await self.get_one_or_none(token=token)
        if reset_token is None:
            msg = "Password reset token not found"
            raise NotFoundException(detail=msg)

        # Check if token is already used
        if reset_token.is_used:
            msg = "Password reset token has already been used"
            raise PermissionDeniedException(detail=msg)

        # Check if token is expired
        if reset_token.is_expired:
            msg = "Password reset token has expired"
            raise PermissionDeniedException(detail=msg)

        # Mark token as used
        await self.update(
            item_id=reset_token.id,
            data={
                "is_used": True,
                "used_at": datetime.now(UTC),
            }
        )

        # Load the user
        user = reset_token.user

        return user

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired password reset tokens.

        Returns:
            Number of tokens deleted
        """
        # Find all expired tokens
        current_time = datetime.now(UTC)
        expired_tokens, _ = await self.list_and_count(
            m.PasswordResetToken.expires_at < current_time
        )

        # Delete expired tokens
        count = 0
        for token in expired_tokens:
            await self.delete(token.id)
            count += 1

        return count

    async def get_user_pending_token(self, user_id: UUID) -> m.PasswordResetToken | None:
        """Get the most recent pending password reset token for a user.

        Args:
            user_id: The user's ID

        Returns:
            The most recent pending token, or None if none exists
        """
        tokens, _ = await self.list_and_count(
            m.PasswordResetToken.user_id == user_id,
            m.PasswordResetToken.is_used == False,  # noqa: E712
        )

        # Sort by created_at descending (most recent first) and return the first non-expired token
        sorted_tokens = sorted(
            tokens, key=lambda t: t.created_at, reverse=True)
        for token in sorted_tokens:
            if not token.is_expired:
                return token

        return None