"""Adaptation loop scaffolding for ACE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from .delta import DeltaOperation


class EnvironmentEvaluator(Protocol):
    """Protocol describing environment verdict callbacks."""

    async def evaluate(self, trace: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(slots=True)
class OfflineAdapter:
    """Offline training loop placeholder."""

    evaluator: EnvironmentEvaluator

    async def run(self, dataset: Sequence[dict[str, Any]]) -> list[DeltaOperation]:
        deltas: list[DeltaOperation] = []
        for sample in dataset:
            verdict = await self.evaluator.evaluate(sample)
            deltas.extend(verdict.get("deltas", []))
        return deltas


@dataclass(slots=True)
class OnlineAdapter:
    """Online learning loop placeholder."""

    evaluator: EnvironmentEvaluator

    async def handle_event(self, trace: dict[str, Any]) -> dict[str, Any]:
        return await self.evaluator.evaluate(trace)


__all__ = ("EnvironmentEvaluator", "OfflineAdapter", "OnlineAdapter")
