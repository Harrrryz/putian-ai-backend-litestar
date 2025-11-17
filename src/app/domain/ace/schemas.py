"""Pydantic schemas for ACE playbook payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlaybookBulletRead(BaseModel):
    """Serializable view of a playbook bullet."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    bullet_id: str
    section_name: str
    section_display_name: str
    content: str
    helpful_count: int
    harmful_count: int
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class PlaybookSectionRead(BaseModel):
    """Serializable view of a playbook section and its bullets."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str
    display_name: str
    description: str | None = None
    ordering: int
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    bullets: list[PlaybookBulletRead] = Field(default_factory=list)


class PlaybookSnapshotRead(BaseModel):
    """Collection of ordered playbook sections and bullet lookups."""

    sections: list[PlaybookSectionRead]
    bullets: dict[str, PlaybookBulletRead]
