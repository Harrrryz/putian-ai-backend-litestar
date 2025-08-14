"""Dependency providers for agent_sessions domain."""

from __future__ import annotations

from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domain.agent_sessions.services import AgentSessionService, SessionMessageService
from app.lib.deps import create_service_provider

# Agent Session service provider with eager loading
provide_agent_session_service = create_service_provider(
    AgentSessionService,
    load=[
        joinedload(m.AgentSession.user, innerjoin=True),
        selectinload(m.AgentSession.messages),
    ],
    error_messages={
        "duplicate_key": "Agent session with this session_id already exists for this user.",
        "integrity": "Agent session operation failed.",
    },
)

# Session Message service provider with eager loading
provide_session_message_service = create_service_provider(
    SessionMessageService,
    load=[
        joinedload(m.SessionMessage.session, innerjoin=True).options(
            joinedload(m.AgentSession.user, innerjoin=True)
        ),
    ],
    error_messages={
        "duplicate_key": "Message operation failed.",
        "integrity": "Message operation failed.",
    },
)
