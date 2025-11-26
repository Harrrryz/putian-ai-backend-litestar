"""Agent factory for creating todo agents.

This module contains the factory function for creating a configured
todo agent with all necessary tools and configurations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.config import get_settings

from .system_instructions import TODO_SYSTEM_INSTRUCTIONS
from .tool_definitions import (
    get_crud_tool_definitions,
    get_schedule_tool_definitions,
    get_support_tool_definitions,
    get_tool_definitions,
)

if TYPE_CHECKING:
    from agents import Agent, Tool

__all__ = [
    "get_todo_agent",
    "get_todo_crud_agent",
    "get_todo_schedule_agent",
    "get_todo_support_agent",
    "get_agent_by_name",
]


def _build_agent(name: str, tools: list["Tool"]) -> "Agent":
    from agents import Agent
    from agents.extensions.models.litellm_model import LitellmModel

    settings = get_settings()

    model = LitellmModel(
        model="openai/glm-4.5",
        api_key=settings.ai.GLM_API_KEY,
        base_url=settings.ai.GLM_BASE_URL,
    )

    return Agent(
        name=name,
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=tools,
    )


def get_todo_agent() -> Agent:
    """Create and return a configured todo agent with LiteLLM."""
    tools = cast("list[Tool]", list(get_tool_definitions()))
    return _build_agent("TodoAssistant", tools)


def get_todo_crud_agent() -> Agent:
    """Create a CRUD-focused todo agent (create, update, delete)."""
    tools = cast("list[Tool]", list(get_crud_tool_definitions()))
    return _build_agent("TodoCrudAssistant", tools)


def get_todo_schedule_agent() -> Agent:
    """Create a scheduling/search todo agent."""
    tools = cast("list[Tool]", list(get_schedule_tool_definitions()))
    return _build_agent("TodoScheduleAssistant", tools)


def get_todo_support_agent() -> Agent:
    """Create a support/auxiliary todo agent (quota and future helpers)."""
    tools = cast("list[Tool]", list(get_support_tool_definitions()))
    return _build_agent("TodoSupportAssistant", tools)


def get_agent_by_name(name: str) -> Agent:
    """Create an agent instance by name, falling back to the default."""
    builders = {
        "TodoAssistant": get_todo_agent,
        "TodoCrudAssistant": get_todo_crud_agent,
        "TodoScheduleAssistant": get_todo_schedule_agent,
        "TodoSupportAssistant": get_todo_support_agent,
    }

    builder = builders.get(name) or get_todo_agent
    return builder()
