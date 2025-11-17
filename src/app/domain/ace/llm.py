"""LLM abstraction layer for ACE roles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class LLMResponse:
    """Normalized response returned by an LLM provider."""

    content: str
    model: str
    latency_ms: int | None = None
    metadata: dict[str, Any] | None = None


class LLMClient(Protocol):
    """Minimal protocol all ACE roles rely on."""

    async def generate(self, prompt: str, **kwargs: Any) -> LLMResponse: ...
