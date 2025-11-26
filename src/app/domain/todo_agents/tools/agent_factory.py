"""Agent factory for creating todo agents.

This module contains the factory function for creating a configured
todo agent with all necessary tools and configurations.
"""

from __future__ import annotations

from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

from app.config import get_settings

from .specialized_agents import get_crud_agent, get_scheduling_agent
from .system_instructions import ORCHESTRATOR_INSTRUCTIONS
from .tool_definitions import get_utility_tools

__all__ = [
    "get_todo_agent",
]


def get_todo_agent(*, instructions: str | None = None) -> Agent:
    """Create and return a configured todo agent with LiteLLM."""
    settings = get_settings()

    model = LitellmModel(
        model="openai/glm-4.5",
        api_key=settings.ai.GLM_API_KEY,
        base_url=settings.ai.GLM_BASE_URL,
    )

    # Build specialized agents that will be exposed as tools
    scheduling_agent = get_scheduling_agent()
    crud_agent = get_crud_agent()

    tools = [
        *get_utility_tools(),
        scheduling_agent.as_tool(
            tool_name="scheduling_specialist",
            tool_description=(
                "Handles schedule analysis, conflict detection, and intelligent "
                "time allocation for tasks. Use this when you need to find or "
                "optimize time slots."
            ),
        ),
        crud_agent.as_tool(
            tool_name="crud_specialist",
            tool_description=(
                "Handles creating, updating, deleting, and listing todos. Use "
                "this when you need to modify or inspect todo items."
            ),
        ),
    ]

    return Agent(
        name="TodoAssistant",
        instructions=instructions or ORCHESTRATOR_INSTRUCTIONS,
        model=model,
        tools=tools,
    )
