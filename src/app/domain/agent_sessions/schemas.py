"""Schemas for agent_sessions domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.accounts.schemas import PydanticBaseModel

if TYPE_CHECKING:
    from datetime import datetime

    from app.db.models.session_message import MessageRole

__all__ = (
    "AgentSessionCreate",
    "AgentSessionSchema",
    "AgentSessionUpdate",
    "SessionConversationRequest",
    "SessionConversationResponse",
    "SessionMessageCreate",
    "SessionMessageSchema",
    "SessionMessageUpdate",
)


class AgentSessionSchema(PydanticBaseModel):
    """Schema for reading agent session."""

    id: "UUID"
    session_id: str
    session_name: str | None = None
    description: str | None = None
    is_active: bool
    user_id: "UUID"
    agent_name: str | None = None
    agent_instructions: str | None = None
    created_at: "datetime"
    updated_at: "datetime"


class AgentSessionCreate(PydanticBaseModel):
    """Schema for creating agent session."""

    session_id: str = Field(..., min_length=1, max_length=255,
                            description="Unique session identifier")
    session_name: str | None = Field(
        None, max_length=255, description="Human-readable session name")
    description: str | None = Field(
        None, max_length=1000, description="Optional session description")
    is_active: bool = Field(
        default=True, description="Whether the session is active")
    agent_name: str | None = Field(
        None, max_length=255, description="Name of the AI agent")
    agent_instructions: str | None = Field(
        None, description="Instructions for the AI agent")


class AgentSessionUpdate(PydanticBaseModel):
    """Schema for updating agent session."""

    session_name: str | None = Field(
        None, max_length=255, description="Human-readable session name")
    description: str | None = Field(
        None, max_length=1000, description="Optional session description")
    is_active: bool | None = Field(
        None, description="Whether the session is active")
    agent_name: str | None = Field(
        None, max_length=255, description="Name of the AI agent")
    agent_instructions: str | None = Field(
        None, description="Instructions for the AI agent")


class SessionMessageSchema(PydanticBaseModel):
    """Schema for reading session message."""

    id: "UUID"
    role: "MessageRole"
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    extra_data: str | None = None
    session_id: "UUID"
    created_at: "datetime"
    updated_at: "datetime"


class SessionMessageCreate(PydanticBaseModel):
    """Schema for creating session message."""

    role: "MessageRole" = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, description="Message content")
    tool_call_id: str | None = Field(
        None, max_length=255, description="Tool call identifier")
    tool_name: str | None = Field(
        None, max_length=255, description="Name of the tool used")
    extra_data: str | None = Field(
        None, description="Additional metadata as JSON string")


class SessionMessageUpdate(PydanticBaseModel):
    """Schema for updating session message."""

    content: str | None = Field(
        None, min_length=1, description="Message content")
    extra_data: str | None = Field(
        None, description="Additional metadata as JSON string")


class SessionConversationRequest(BaseModel):
    """Request schema for agent conversation."""

    model_config = ConfigDict(extra="forbid")

    messages: list[dict[str, Any]
                   ] = Field(..., description="List of conversation messages")
    session_id: str | None = Field(
        None, description="Optional session ID for conversation persistence")
    session_name: str | None = Field(
        None, description="Optional human-readable session name")


class SessionConversationResponse(BaseModel):
    """Response schema for agent conversation."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Session identifier")
    session_uuid: UUID = Field(..., description="Session UUID")
    response: str = Field(..., description="Agent response")
    messages_count: int = Field(...,
                                description="Total number of messages in session")
    session_active: bool = Field(...,
                                 description="Whether the session is active")
