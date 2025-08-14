"""Controllers for session message management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from litestar import Controller, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Dependency, Parameter

from app.domain.agent_sessions import urls
from app.domain.agent_sessions.deps import provide_session_message_service, provide_agent_session_service
from app.domain.agent_sessions.schemas import (
    SessionMessageCreate,
    SessionMessageSchema,
    SessionMessageUpdate,
)
from app.lib.deps import create_filter_dependencies

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service import OffsetPagination

    from app.db import models as m
    from app.domain.agent_sessions.services import SessionMessageService, AgentSessionService


class SessionMessageController(Controller):
    """Controller for session message operations."""

    tags = ["Session Messages"]
    dependencies = {
        "message_service": Provide(provide_session_message_service),
        "session_service": Provide(provide_agent_session_service),
    } | create_filter_dependencies(
        {
            "id_filter": UUID,
            "search": "content",
            "pagination_type": "limit_offset",
            "pagination_size": 50,
            "created_at": True,
            "updated_at": True,
            "sort_field": "created_at",
            "sort_order": "asc",
        },
    )

    @get(operation_id="ListSessionMessages", path=urls.SESSION_MESSAGES_LIST)
    async def list_messages(
        self,
        current_user: "m.User",
        message_service: SessionMessageService,
        session_service: AgentSessionService,
        session_id: UUID = Parameter(
            title="Session ID", description="The agent session ID"),
        filters: Annotated[list["FilterTypes"], Dependency(
            skip_validation=True)] | None = None,
    ) -> "OffsetPagination[SessionMessageSchema]":
        """List all messages for a specific session."""
        # First verify the session belongs to the user
        session = await session_service.get(session_id)
        if session.user_id != current_user.id:
            msg = "Session not found"
            raise ValueError(msg)

        from app.db import models as m
        session_filter = m.SessionMessage.session_id == session_id
        results, total = await message_service.list_and_count(session_filter, *(filters or []))
        return message_service.to_schema(data=results, total=total, schema_type=SessionMessageSchema, filters=filters or [])

    @post(operation_id="CreateSessionMessage", path=urls.SESSION_MESSAGES_CREATE)
    async def create_message(
        self,
        current_user: "m.User",
        message_service: SessionMessageService,
        session_service: AgentSessionService,
        data: SessionMessageCreate,
        session_id: UUID = Parameter(
            title="Session ID", description="The agent session ID"),
    ) -> SessionMessageSchema:
        """Create a new message in a session."""
        # First verify the session belongs to the user
        session = await session_service.get(session_id)
        if session.user_id != current_user.id:
            msg = "Session not found"
            raise ValueError(msg)

        message_dict = data.to_dict()
        message_dict["session_id"] = session_id
        obj = await message_service.create(message_dict)
        return message_service.to_schema(schema_type=SessionMessageSchema, data=obj)

    @get(operation_id="GetSessionMessage", path=urls.SESSION_MESSAGES_DETAIL)
    async def get_message(
        self,
        current_user: "m.User",
        message_service: SessionMessageService,
        session_service: AgentSessionService,
        session_id: UUID = Parameter(
            title="Session ID", description="The agent session ID"),
        message_id: UUID = Parameter(
            title="Message ID", description="The session message ID"),
    ) -> SessionMessageSchema:
        """Get a specific message from a session."""
        # First verify the session belongs to the user
        session = await session_service.get(session_id)
        if session.user_id != current_user.id:
            msg = "Session not found"
            raise ValueError(msg)

        obj = await message_service.get(message_id)

        # Verify the message belongs to the session
        if obj.session_id != session_id:
            msg = "Message not found"
            raise ValueError(msg)

        return message_service.to_schema(schema_type=SessionMessageSchema, data=obj)

    @patch(operation_id="UpdateSessionMessage", path=urls.SESSION_MESSAGES_DETAIL)
    async def update_message(
        self,
        current_user: "m.User",
        message_service: SessionMessageService,
        session_service: AgentSessionService,
        data: SessionMessageUpdate,
        session_id: UUID = Parameter(
            title="Session ID", description="The agent session ID"),
        message_id: UUID = Parameter(
            title="Message ID", description="The session message ID"),
    ) -> SessionMessageSchema:
        """Update a message in a session."""
        # First verify the session belongs to the user
        session = await session_service.get(session_id)
        if session.user_id != current_user.id:
            msg = "Session not found"
            raise ValueError(msg)

        obj = await message_service.get(message_id)

        # Verify the message belongs to the session
        if obj.session_id != session_id:
            msg = "Message not found"
            raise ValueError(msg)

        obj = await message_service.update(obj, **data.to_dict())
        return message_service.to_schema(schema_type=SessionMessageSchema, data=obj)

    @delete(operation_id="DeleteSessionMessage", path=urls.SESSION_MESSAGES_DETAIL)
    async def delete_message(
        self,
        current_user: "m.User",
        message_service: SessionMessageService,
        session_service: AgentSessionService,
        session_id: UUID = Parameter(
            title="Session ID", description="The agent session ID"),
        message_id: UUID = Parameter(
            title="Message ID", description="The session message ID"),
    ) -> None:
        """Delete a message from a session."""
        # First verify the session belongs to the user
        session = await session_service.get(session_id)
        if session.user_id != current_user.id:
            msg = "Session not found"
            raise ValueError(msg)

        obj = await message_service.get(message_id)

        # Verify the message belongs to the session
        if obj.session_id != session_id:
            msg = "Message not found"
            raise ValueError(msg)

        await message_service.delete(message_id)

    @delete(operation_id="ClearSessionMessages", path=urls.SESSION_CLEAR_MESSAGES)
    async def clear_messages(
        self,
        current_user: "m.User",
        message_service: SessionMessageService,
        session_service: AgentSessionService,
        session_id: UUID = Parameter(
            title="Session ID", description="The agent session ID"),
    ) -> dict[str, int]:
        """Clear all messages from a session."""
        # First verify the session belongs to the user
        session = await session_service.get(session_id)
        if session.user_id != current_user.id:
            msg = "Session not found"
            raise ValueError(msg)

        deleted_count = await message_service.clear_session_messages(session_id)
        return {"deleted_count": deleted_count}
