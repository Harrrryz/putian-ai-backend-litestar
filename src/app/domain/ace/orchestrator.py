"""ACE orchestration helpers for runtime integrations."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Sequence

from structlog import get_logger

from .delta import DeltaAction, DeltaOperation
from .playbook import (
    AcePlaybookService,
    PlaybookBullet,
    PlaybookDeltaResult,
)

logger = get_logger(__name__)

ACE_TAG_PATTERN = re.compile(r"\[ACE:([a-zA-Z0-9_.-]+)\]")


@dataclass(slots=True)
class AceContextBlock:
    """Represents a formatted block of instructions plus the referenced bullets."""

    instructions: str
    bullet_ids: list[str]


class AceOrchestrator:
    """Enrich agent prompts with playbook context and capture feedback."""

    def __init__(
        self,
        playbook_service: AcePlaybookService,
        *,
        max_strategies: int = 5,
        applied_by: str = "ace-orchestrator",
    ) -> None:
        self._playbook_service = playbook_service
        self._max_strategies = max(1, max_strategies)
        self._applied_by = applied_by

    async def build_context_block(self) -> AceContextBlock | None:
        """Return a formatted instruction appendix describing top strategies."""
        snapshot = await self._playbook_service.get_snapshot()
        if not snapshot.bullets:
            return None

        sorted_bullets = sorted(
            snapshot.bullets.values(),
            key=lambda bullet: (
                bullet.helpful_count - bullet.harmful_count,
                bullet.created_at,
            ),
            reverse=True,
        )
        selected = list(itertools.islice(sorted_bullets, self._max_strategies))
        if not selected:
            return None

        instructions = self._format_instructions(selected)
        bullet_ids = [bullet.bullet_id for bullet in selected]
        return AceContextBlock(instructions=instructions, bullet_ids=bullet_ids)

    def merge_instructions(self, base: str, block: AceContextBlock | None) -> str:
        """Append ACE block to base instructions if available."""
        if block is None:
            return base
        return f"{base}\n\n{block.instructions}"

    async def record_feedback(
        self,
        bullet_ids: Sequence[str],
        *,
        success: bool,
        reason: str | None = None,
    ) -> PlaybookDeltaResult | None:
        """Apply TAG deltas for referenced bullets."""
        unique_bullets = list(dict.fromkeys(bullet_ids))
        if not unique_bullets:
            return None

        ops = []
        for bullet_id in unique_bullets:
            ops.append(
                DeltaOperation(
                    action=DeltaAction.TAG,
                    bullet_id=bullet_id,
                    helpful_delta=1 if success else 0,
                    harmful_delta=0 if success else 1,
                )
            )
        description = reason or ("ACE success" if success else "ACE remediation")
        return await self._playbook_service.apply_deltas(
            ops,
            applied_by=self._applied_by,
            description=description,
        )

    @staticmethod
    def extract_strategy_mentions(text: str | None) -> list[str]:
        """Extract referenced bullet IDs from agent output."""
        if not text:
            return []
        return ACE_TAG_PATTERN.findall(text)

    def _format_instructions(self, bullets: Sequence[PlaybookBullet]) -> str:
        """Render a stable instruction block for the agent."""
        lines = [
            "ACE Strategy Playbook:",
            "When you leverage a strategy, cite it as [ACE:<strategy_id>] so reflections can track usage.",
        ]
        for bullet in bullets:
            lines.append(
                f"- [ACE:{bullet.bullet_id}] ({bullet.section_display_name}) {bullet.content.strip()}"
            )
        return "\n".join(lines)


__all__ = ("AceContextBlock", "AceOrchestrator")
