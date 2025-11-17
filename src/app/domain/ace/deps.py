"""Dependency providers for ACE domain services."""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.db import models as m
from app.lib.deps import create_service_provider

from .playbook import AcePlaybookService
from .services import (
    AcePlaybookBulletService,
    AcePlaybookRevisionService,
    AcePlaybookSectionService,
)

provide_ace_playbook_service = create_service_provider(
    AcePlaybookService,
    load=[joinedload(m.AcePlaybookBullet.section)],
)

provide_ace_playbook_section_service = create_service_provider(
    AcePlaybookSectionService,
)

provide_ace_playbook_revision_service = create_service_provider(
    AcePlaybookRevisionService,
)

provide_ace_playbook_bullet_service = create_service_provider(
    AcePlaybookBulletService,
    load=[joinedload(m.AcePlaybookBullet.section)],
)

__all__ = (
    "provide_ace_playbook_bullet_service",
    "provide_ace_playbook_revision_service",
    "provide_ace_playbook_section_service",
    "provide_ace_playbook_service",
)
