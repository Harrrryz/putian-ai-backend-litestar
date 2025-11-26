"""Specialized agents for the todo application.

This module defines specialized agents (Scheduling, CRUD) that can be used
as tools by the main agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

from app.config import get_settings

from .tool_definitions import get_crud_tools, get_scheduling_tools

if TYPE_CHECKING:
    from agents import Tool

__all__ = [
    "get_crud_agent",
    "get_scheduling_agent",
]


def get_scheduling_agent() -> Agent:
    """Create and return a configured Scheduling Agent."""
    settings = get_settings()

    model = LitellmModel(
        model="openai/glm-4.5",
        api_key=settings.ai.GLM_API_KEY,
        base_url=settings.ai.GLM_BASE_URL,
    )

    tools = cast("list[Tool]", list(get_scheduling_tools()))

    return Agent(
        name="SchedulingSpecialist",
        instructions=(
            "You are an expert scheduler. Your only job is to find the best time slots "
            "for tasks and manage the user's schedule. You have access to tools for "
            "analyzing the schedule and adding/updating events. "
            "Always check for conflicts before scheduling."
        ),
        model=model,
        tools=tools,
    )


def get_crud_agent() -> Agent:
    """Create and return a configured CRUD Agent."""
    settings = get_settings()

    model = LitellmModel(
        model="openai/glm-4.5",
        api_key=settings.ai.GLM_API_KEY,
        base_url=settings.ai.GLM_BASE_URL,
    )

    tools = cast("list[Tool]", list(get_crud_tools()))

    return Agent(
        name="TodoCRUDAssistant",
        instructions=(
            "You are a specialized assistant for managing Todo items. "
            "You can create, update, delete, and list todos. "
            "Focus on accurate data entry and management."
        ),
        model=model,
        tools=tools,
    )
