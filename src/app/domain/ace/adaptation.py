"""Adaptation loop implementation for ACE."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from .playbook import AcePlaybookService, PlaybookDeltaResult
from .roles import (
    CuratorRole,
    GeneratorPayload,
    GeneratorResult,
    GeneratorRole,
    ReflectorPayload,
    ReflectorRole,
)


class EnvironmentEvaluator(Protocol):
    """Protocol describing environment verdict callbacks."""

    async def evaluate(self, trace: dict[str, Any]) -> dict[str, Any]: ...


class OfflineAdapter:
    """Offline training loop that replays datasets through ACE roles."""

    def __init__(
        self,
        *,
        evaluator: EnvironmentEvaluator,
        playbook_service: AcePlaybookService,
        generator: GeneratorRole,
        reflector: ReflectorRole,
        curator: CuratorRole,
    ) -> None:
        self._evaluator = evaluator
        self._playbook_service = playbook_service
        self._generator = generator
        self._reflector = reflector
        self._curator = curator

    async def run(self, dataset: Sequence[dict[str, Any]]) -> list[PlaybookDeltaResult]:
        results: list[PlaybookDeltaResult] = []
        for sample in dataset:
            generator_payload = GeneratorPayload(
                question=sample.get("question", ""),
                context=sample.get("context", ""),
                strategies=sample.get("strategies", []),
            )
            generation = await self._generator.run(generator_payload)
            env_feedback = await self._evaluator.evaluate(
                {
                    "sample": sample,
                    "generator_result": generation.model_dump(),
                }
            )
            reflection = await self._reflector.run(
                ReflectorPayload(
                    question=generator_payload.question,
                    generator_result=generation,
                    environment_feedback=env_feedback,
                )
            )
            operations = await self._curator.run(reflection)
            if not operations:
                continue
            result = await self._playbook_service.apply_deltas(
                operations,
                applied_by="offline-adapter",
                description=sample.get("description"),
                metadata={"dataset": sample.get("dataset", "offline")},
            )
            if result:
                results.append(result)
        return results


class OnlineAdapter:
    """Online learning loop that runs per event."""

    def __init__(
        self,
        *,
        evaluator: EnvironmentEvaluator,
        playbook_service: AcePlaybookService,
        generator: GeneratorRole,
        reflector: ReflectorRole,
        curator: CuratorRole,
    ) -> None:
        self._evaluator = evaluator
        self._playbook_service = playbook_service
        self._generator = generator
        self._reflector = reflector
        self._curator = curator

    async def handle_event(self, trace: dict[str, Any]) -> PlaybookDeltaResult | None:
        """Process a single live trace."""
        generator_result = await self._ensure_generation(trace)
        env_feedback = await self._evaluator.evaluate(
            {
                "trace": trace,
                "generator_result": generator_result.model_dump(),
            }
        )
        reflection = await self._reflector.run(
            ReflectorPayload(
                question=trace.get("question", ""),
                generator_result=generator_result,
                environment_feedback=env_feedback,
            )
        )
        operations = await self._curator.run(reflection)
        if not operations:
            return None
        return await self._playbook_service.apply_deltas(
            operations,
            applied_by="online-adapter",
            description=trace.get("description"),
            metadata={"session_id": trace.get("session_id")},
        )

    async def _ensure_generation(self, trace: dict[str, Any]) -> GeneratorResult:
        generator_payload = trace.get("generator_payload")
        raw_result = trace.get("generator_result")
        if raw_result:
            return GeneratorResult(**raw_result)
        payload = GeneratorPayload(
            question=trace.get("question", ""),
            context=trace.get("context", ""),
            strategies=trace.get("strategies", []),
        )
        return await self._generator.run(payload)


__all__ = ("EnvironmentEvaluator", "OfflineAdapter", "OnlineAdapter")
