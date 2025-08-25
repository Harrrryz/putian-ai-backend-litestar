"""Agent factory for creating todo agents.

This module contains the factory function for creating a configured
todo agent with all necessary tools and configurations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.config import get_settings

from .system_instructions import TODO_SYSTEM_INSTRUCTIONS
from .tool_definitions import get_tool_definitions

if TYPE_CHECKING:
    from agents import Agent, Tool

__all__ = [
    "get_todo_agent",
]


def get_todo_agent() -> Agent:
    """Create and return a configured todo agent with all tools."""
    from agents import Agent, OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    settings = get_settings()
    model = OpenAIChatCompletionsModel(
        model="doubao-1.5-pro-32k-250115",
        openai_client=AsyncOpenAI(
            api_key=settings.ai.VOLCENGINE_API_KEY,
            base_url=settings.ai.VOLCENGINE_BASE_URL,
        ),
    )

    tools = cast("list[Tool]", list(get_tool_definitions()))

    return Agent(
        name="TodoAssistant",
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=tools,
    )
