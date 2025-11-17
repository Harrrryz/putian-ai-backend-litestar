from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AcePlaybookSection(UUIDAuditBase):
    """Logical grouping for ACE playbook bullets."""

    __tablename__ = "ace_playbook_section"
    __table_args__ = (
        UniqueConstraint("name", name="uq_ace_playbook_section_name"),
        {"comment": "ACE playbook sections"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordering: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON(),
        nullable=False,
        default=dict,
    )

    bullets: Mapped[list["AcePlaybookBullet"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AcePlaybookBullet.created_at",
    )


class AcePlaybookBullet(UUIDAuditBase):
    """Individual ACE strategies stored in the playbook."""

    __tablename__ = "ace_playbook_bullet"
    __table_args__ = (
        UniqueConstraint("bullet_id", name="uq_ace_playbook_bullet_identifier"),
        Index("ix_ace_playbook_bullet_section_created_at", "section_id", "created_at"),
        {"comment": "ACE playbook bullets"},
    )

    bullet_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section_id: Mapped[UUID] = mapped_column(
        ForeignKey("ace_playbook_section.id", ondelete="CASCADE"),
        nullable=False,
    )
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    harmful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON(),
        nullable=False,
        default=dict,
    )

    section: Mapped[AcePlaybookSection] = relationship(
        back_populates="bullets",
        lazy="joined",
    )


class AcePlaybookRevision(UUIDAuditBase):
    """Audit log entries describing mutations to the playbook."""

    __tablename__ = "ace_playbook_revision"
    __table_args__ = (
        Index("ix_ace_playbook_revision_created_at", "created_at"),
        {"comment": "ACE playbook delta revisions"},
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON(),
        nullable=False,
        default=list,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON(),
        nullable=False,
        default=dict,
    )


__all__ = (
    "AcePlaybookBullet",
    "AcePlaybookRevision",
    "AcePlaybookSection",
)
