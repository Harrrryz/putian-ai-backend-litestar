"""Delta operation definitions for ACE playbooks."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeltaAction(StrEnum):
    """Supported delta operation types."""

    ADD = "ADD"
    UPDATE = "UPDATE"
    TAG = "TAG"
    REMOVE = "REMOVE"


class DeltaOperation(BaseModel):
    """Normalized mutation request for a single playbook bullet."""

    model_config = ConfigDict(extra="forbid")

    action: DeltaAction
    bullet_id: str = Field(..., min_length=1, max_length=128)
    section_name: str | None = Field(
        default=None,
        description="Target section for ADD/UPDATE operations.",
    )
    section_display_name: str | None = Field(
        default=None,
        description="Optional human-friendly label for the section.",
    )
    content: str | None = Field(
        default=None,
        description="Strategy text for ADD/UPDATE operations.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary metadata describing the strategy.",
    )
    helpful_delta: int = Field(
        default=0,
        description="Helpful counter delta used by TAG operations.",
    )
    harmful_delta: int = Field(
        default=0,
        description="Harmful counter delta used by TAG operations.",
    )

    @model_validator(mode="after")
    def _validate_action(self) -> "DeltaOperation":
        """Ensure that each action receives the required payload."""
        if self.action is DeltaAction.ADD:
            if not self.section_name:
                msg = "ADD operations require section_name"
                raise ValueError(msg)
            if not self.content:
                msg = "ADD operations require content"
                raise ValueError(msg)
        if self.action is DeltaAction.UPDATE:
            if not any(
                (
                    self.section_name,
                    self.section_display_name,
                    self.content,
                    self.metadata is not None,
                )
            ):
                msg = "UPDATE operations must include content, metadata, or section updates"
                raise ValueError(msg)
        if self.action is DeltaAction.TAG:
            if self.helpful_delta == 0 and self.harmful_delta == 0:
                msg = "TAG operations must include helpful_delta or harmful_delta"
                raise ValueError(msg)
        return self

    def dedupe_key(self) -> Tuple[DeltaAction, str]:
        """Provide a stable key for deduplicating batch operations."""
        return (self.action, self.bullet_id)
