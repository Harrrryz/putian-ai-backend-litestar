"""Role scaffolding for ACE Generator, Reflector, and Curator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .llm import LLMClient, LLMResponse


class Role(Protocol):
    """Shared interface for ACE roles."""

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(slots=True)
class GeneratorRole:
    """Placeholder Generator implementation."""

    llm: LLMClient

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        response: LLMResponse = await self.llm.generate(payload["prompt"])
        return {"response": response.content, "model": response.model}


@dataclass(slots=True)
class ReflectorRole:
    """Placeholder Reflector implementation."""

    llm: LLMClient

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = await self.llm.generate(payload["prompt"])
        return {"analysis": "pending"}


@dataclass(slots=True)
class CuratorRole:
    """Placeholder Curator implementation."""

    llm: LLMClient

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = await self.llm.generate(payload["prompt"])
        return {"deltas": []}


__all__ = ("CuratorRole", "GeneratorRole", "ReflectorRole", "Role")
