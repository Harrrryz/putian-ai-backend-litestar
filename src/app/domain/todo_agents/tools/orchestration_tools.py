"""Orchestration tools for the main agent to delegate tasks to specialized agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents import FunctionTool, Runner

from .argument_models import ConsultCrudAgentArgs, ConsultSchedulerArgs
from .shared import preprocess_args
from .specialized_agents import get_crud_agent, get_scheduling_agent

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agents import RunContextWrapper

__all__ = [
    "get_orchestration_tools",
]


async def consult_scheduler_impl(ctx: RunContextWrapper, args: str) -> str:
    """Delegate a scheduling request to the Scheduling Specialist."""
    args = preprocess_args(args)
    parsed = ConsultSchedulerArgs.model_validate_json(args)

    agent = get_scheduling_agent()

    # We use a sub-session ID to allow the specialist to maintain some context
    # if called multiple times within the same parent session.
    # Note: We are using a simple in-memory session for the sub-agent for now.
    # If persistence is needed, we would need access to the session DB path.

    # Run the agent
    result = await Runner.run(agent, parsed.request)

    return f"Scheduling Specialist response: {result.final_output}"


async def consult_crud_agent_impl(ctx: RunContextWrapper, args: str) -> str:
    """Delegate a CRUD request to the CRUD Assistant."""
    args = preprocess_args(args)
    parsed = ConsultCrudAgentArgs.model_validate_json(args)

    agent = get_crud_agent()

    # Run the agent
    result = await Runner.run(agent, parsed.request)

    return f"CRUD Assistant response: {result.final_output}"


def get_orchestration_tools() -> Sequence[FunctionTool]:
    """Return the list of orchestration tools."""

    consult_scheduler_tool = FunctionTool(
        name="consult_scheduler",
        description=(
            "Delegate complex scheduling tasks to a specialist agent. "
            "Use this when the user asks to schedule something, analyze the schedule, "
            "or find free time. The specialist has access to calendar tools."
        ),
        params_json_schema=ConsultSchedulerArgs.model_json_schema(),
        on_invoke_tool=consult_scheduler_impl,
    )

    consult_crud_agent_tool = FunctionTool(
        name="consult_crud_agent",
        description=(
            "Delegate Todo management tasks to a specialist agent. "
            "Use this when the user asks to create, update, delete, or list todos. "
            "The specialist has access to database tools."
        ),
        params_json_schema=ConsultCrudAgentArgs.model_json_schema(),
        on_invoke_tool=consult_crud_agent_impl,
    )

    return [
        consult_scheduler_tool,
        consult_crud_agent_tool,
    ]
