"""Tool definitions for todo agent.

This module contains the FunctionTool definitions that expose the
implementation functions to the agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agents import FunctionTool

from .argument_models import (
    AnalyzeScheduleArgs,
    BatchUpdateScheduleArgs,
    CreateTodoArgs,
    DeleteTodoArgs,
    GetTodoListArgs,
    GetUserDatetimeArgs,
    GetUserQuotaArgs,
    ScheduleTodoArgs,
    UpdateTodoArgs,
)
from .tool_implementations import (
    analyze_schedule_impl,
    batch_update_schedule_impl,
    create_todo_impl,
    delete_todo_impl,
    get_todo_list_impl,
    get_user_quota_impl,
    schedule_todo_impl,
    update_todo_impl,
)
from .universal_tools import get_user_datetime_impl

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agents import FunctionTool

__all__ = [
    "get_tool_definitions",
]


def get_tool_definitions() -> Sequence[FunctionTool]:
    """Return the list of FunctionTool definitions for the todo agent."""
    from agents import FunctionTool

    create_todo_tool = FunctionTool(
        name="create_todo",
        description="Create a new todo item using the TodoService.",
        params_json_schema=CreateTodoArgs.model_json_schema(),
        on_invoke_tool=create_todo_impl,
    )

    delete_todo_tool = FunctionTool(
        name="delete_todo",
        description="Delete a todo item using the TodoService.",
        params_json_schema=DeleteTodoArgs.model_json_schema(),
        on_invoke_tool=delete_todo_impl,
    )

    update_todo_tool = FunctionTool(
        name="update_todo",
        description="Update an existing todo item using the TodoService.",
        params_json_schema=UpdateTodoArgs.model_json_schema(),
        on_invoke_tool=update_todo_impl,
    )

    get_todo_list_tool = FunctionTool(
        name="get_todo_list",
        description="Get a list of all todos for the current user.",
        params_json_schema=GetTodoListArgs.model_json_schema(),
        on_invoke_tool=get_todo_list_impl,
    )

    analyze_schedule_tool = FunctionTool(
        name="analyze_schedule",
        description="Analyze the user's schedule to identify free time slots and potential conflicts.",
        params_json_schema=AnalyzeScheduleArgs.model_json_schema(),
        on_invoke_tool=analyze_schedule_impl,
    )

    schedule_todo_tool = FunctionTool(
        name="schedule_todo",
        description="Intelligently schedule a todo by finding optimal time slots based on existing schedule.",
        params_json_schema=ScheduleTodoArgs.model_json_schema(),
        on_invoke_tool=schedule_todo_impl,
    )

    batch_update_schedule_tool = FunctionTool(
        name="batch_update_schedule",
        description="Apply batch schedule updates after user confirmation to resolve conflicts and optimize timing.",
        params_json_schema=BatchUpdateScheduleArgs.model_json_schema(),
        on_invoke_tool=batch_update_schedule_impl,
    )

    get_user_datetime_tool = FunctionTool(
        name="get_user_datetime",
        description="Get the user's current date, time, and timezone information. Use this tool before performing any time-based operations.",
        params_json_schema=GetUserDatetimeArgs.model_json_schema(),
        on_invoke_tool=get_user_datetime_impl,
    )

    get_user_quota_tool = FunctionTool(
        name="get_user_quota",
        description="Get the user's current agent usage quota information including used requests, remaining quota, and reset date.",
        params_json_schema=GetUserQuotaArgs.model_json_schema(),
        on_invoke_tool=get_user_quota_impl,
    )

    return [
        get_user_datetime_tool,  # Universal tool should be first
        get_user_quota_tool,  # Quota information tool
        create_todo_tool,
        delete_todo_tool,
        update_todo_tool,
        get_todo_list_tool,
        analyze_schedule_tool,
        schedule_todo_tool,
        batch_update_schedule_tool,
    ]
