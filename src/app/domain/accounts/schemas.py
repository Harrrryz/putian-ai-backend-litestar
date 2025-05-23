from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, EmailStr, Field

__all__ = (
    "AccountLogin",
    "AccountRegister",
    "Message",
    "User",
    "UserCreate",
    "UserRole",
    "UserRoleAdd",
    "UserRoleRevoke",
    "UserUpdate",
)


class PydanticBaseModel(BaseModel):
    """Base model with camel case config."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda s: "".join(
            [s[0].lower(), *[c if c.islower() else f"_{c.lower()}" for c in s[1:]]]
        ).replace("_", ""),
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class UserRole(PydanticBaseModel):
    """Holds role details for a user.

    This is nested in the User Model for 'roles'
    """

    role_id: UUID
    role_slug: str
    role_name: str
    assigned_at: datetime


class OauthAccount(PydanticBaseModel):
    """Holds linked Oauth details for a user."""

    id: UUID
    oauth_name: str
    access_token: str
    account_id: str
    account_email: str
    expires_at: int | None = None
    refresh_token: str | None = None


class User(PydanticBaseModel):
    """User properties to use for a response."""

    id: UUID
    email: str
    name: str | None = None
    is_superuser: bool = False
    is_active: bool = False
    is_verified: bool = False
    has_password: bool = False
    roles: list[UserRole] = Field(default_factory=list)
    oauth_accounts: list[OauthAccount] = Field(default_factory=list)


class UserCreate(PydanticBaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None
    is_superuser: bool = False
    is_active: bool = True
    is_verified: bool = False


class UserUpdate(PydanticBaseModel):
    email: EmailStr | None = None
    password: str | None = None
    name: str | None = None
    is_superuser: bool | None = None
    is_active: bool | None = None
    is_verified: bool | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda s: "".join(
            [s[0].lower(), *[c if c.islower() else f"_{c.lower()}" for c in s[1:]]]
        ).replace("_", ""),
        extra="ignore",
    )


class AccountLogin(PydanticBaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class AccountRegister(PydanticBaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None


class UserRoleAdd(PydanticBaseModel):
    """User role add ."""

    user_name: str


class UserRoleRevoke(PydanticBaseModel):
    """User role revoke ."""

    user_name: str


class Message(PydanticBaseModel):
    """Message response model."""

    message: str
