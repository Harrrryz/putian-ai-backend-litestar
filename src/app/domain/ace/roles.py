"""Role implementations for ACE Generator, Reflector, and Curator."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from .delta import DeltaAction, DeltaOperation
from .llm import LLMClient, LLMResponse
from .prompts import GENERATOR_PROMPT_V1, REFLECTOR_PROMPT_V1


class GeneratorPayload(BaseModel):
    """Input schema for generator requests."""

    question: str
    context: str = ""
    strategies: list[str] = Field(default_factory=list)


class GeneratorResult(BaseModel):
    """Structured response from the generator."""

    final_answer: str
    reasoning: str | None = None
    strategy_ids: list[str] = Field(default_factory=list)
    model: str | None = None


class StrategyFeedback(BaseModel):
    """Classification data for a single bullet."""

    bullet_id: str
    classification: Literal["helpful", "harmful", "neutral"] = "neutral"
    rationale: str | None = None


class ReflectorPayload(BaseModel):
    """Input schema for the reflector."""

    question: str
    generator_result: GeneratorResult
    environment_feedback: dict[str, Any] = Field(default_factory=dict)


class ReflectionResult(BaseModel):
    """Structured analysis output by the reflector."""

    outcome: Literal["success", "failure", "partial"] = "success"
    insights: str | None = None
    strategy_feedback: list[StrategyFeedback] = Field(default_factory=list)


class GeneratorRole:
    """Generator implementation backed by an LLM client."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(self, payload: GeneratorPayload) -> GeneratorResult:
        prompt = GENERATOR_PROMPT_V1.render(
            question=payload.question,
            context=payload.context or "No extra context provided.",
            strategies="\n".join(payload.strategies) or "No strategies supplied.",
        )
        response: LLMResponse = await self._llm.generate(prompt)
        data = self._parse_json(response.content)
        return GeneratorResult(
            final_answer=data.get("final_answer", response.content),
            reasoning=data.get("reasoning"),
            strategy_ids=data.get("strategy_ids", []),
            model=response.model,
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}


class ReflectorRole:
    """Reflector implementation backed by the LLM client."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(self, payload: ReflectorPayload) -> ReflectionResult:
        prompt = REFLECTOR_PROMPT_V1.render(
            question=payload.question,
            final_answer=payload.generator_result.final_answer,
            environment_feedback=json.dumps(payload.environment_feedback),
        )
        response = await self._llm.generate(prompt)
        data = GeneratorRole._parse_json(response.content)
        feedback = [
            StrategyFeedback(**entry)
            for entry in data.get("strategy_feedback", [])
        ]
        return ReflectionResult(
            outcome=data.get("outcome", "success"),
            insights=data.get("insights"),
            strategy_feedback=feedback,
        )


class CuratorRole:
    """Converts reflections into delta operations."""

    async def run(self, reflection: ReflectionResult) -> list[DeltaOperation]:
        operations: list[DeltaOperation] = []
        for feedback in reflection.strategy_feedback:
            if feedback.classification == "helpful":
                operations.append(
                    DeltaOperation(
                        action=DeltaAction.TAG,
                        bullet_id=feedback.bullet_id,
                        helpful_delta=1,
                    )
                )
            elif feedback.classification == "harmful":
                operations.append(
                    DeltaOperation(
                        action=DeltaAction.TAG,
                        bullet_id=feedback.bullet_id,
                        harmful_delta=1,
                    )
                )
        return operations


__all__ = (
    "CuratorRole",
    "GeneratorPayload",
    "GeneratorResult",
    "GeneratorRole",
    "ReflectionResult",
    "ReflectorPayload",
    "ReflectorRole",
    "StrategyFeedback",
)
