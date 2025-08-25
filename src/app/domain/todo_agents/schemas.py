"""Schemas for todo_agents domain."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.domain.accounts.schemas import PydanticBaseModel

__all__ = (
    "AgentTodoRequest",
    "AgentTodoResponse",
    "AnalyzeScheduleArgs",
    "BatchUpdateScheduleArgs",
    "CreateTodoArgs",
    "DeleteTodoArgs",
    "GetTodoListArgs",
    "ScheduleConflictResolution",
    "ScheduleTodoArgs",
    "SearchTodoArgs",
    "UpdateTodoArgs",
)


class AgentTodoRequest(PydanticBaseModel):
    """Request schema for AI agent todo operations."""

    messages: list[dict[str, Any]
                   ] = Field(..., description="List of conversation messages")
    session_id: str | None = Field(
        None, description="Optional session ID for conversation persistence")
    session_name: str | None = Field(
        None, description="Optional human-readable session name")


class AgentTodoResponse(PydanticBaseModel):
    """Response schema for AI agent todo operations."""

    status: str = Field(...,
                        description="Status of the operation (success/error)")
    message: str = Field(..., description="Agent response message")
    agent_response: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation history")


class CreateTodoArgs(PydanticBaseModel):
    """Schema for creating a todo item via agent."""

    item: str = Field(...,
                      description="The name/title of the todo item to create")
    description: str | None = Field(
        None, description="The description/content of the todo item")
    alarm_time: str | None = Field(
        None,
        description="The alarm time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified"
    )
    start_time: str = Field(
        ..., description="The start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    end_time: str = Field(
        ..., description="The end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    tags: list[str] | None = Field(
        None,
        description="List of tag names to associate with the todo. Common tags: 'work', 'personal', 'study', 'entertainment'"
    )
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(
        None,
        description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
    auto_schedule: bool = Field(
        default=False,
        description="Whether to automatically schedule this todo if no specific time is provided"
    )


class ScheduleTodoArgs(PydanticBaseModel):
    """Schema for scheduling a todo item via agent."""

    item: str = Field(...,
                      description="The name/title of the todo item to schedule")
    description: str | None = Field(
        None, description="The description/content of the todo item")
    target_date: str | None = Field(
        None,
        description="The target date for scheduling (YYYY-MM-DD). If not provided, defaults to today or tomorrow"
    )
    duration_minutes: int = Field(
        default=60, description="Estimated duration of the task in minutes (default: 60)")
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(
        None,
        description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
    preferred_time_of_day: str | None = Field(
        None,
        description="Preferred time of day: 'morning' (8-12), 'afternoon' (12-17), 'evening' (17-21), or specific time range"
    )
    tags: list[str] | None = Field(
        None, description="List of tag names to associate with the todo")


class AnalyzeScheduleArgs(PydanticBaseModel):
    """Schema for analyzing schedule via agent."""

    target_date: str | None = Field(
        None,
        description="The date to analyze (YYYY-MM-DD). If not provided, analyzes today and tomorrow"
    )
    timezone: str | None = Field(
        None,
        description="Timezone for date analysis (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
    include_days: int = Field(
        default=3, description="Number of days to analyze starting from target_date (default: 3)")


class ScheduleConflictResolution(PydanticBaseModel):
    """Schema for schedule conflict resolution."""

    todo_id: str = Field(..., description="The UUID of the todo to reschedule")
    new_time: str = Field(...,
                          description="New time in format YYYY-MM-DD HH:MM:SS")
    reason: str = Field(..., description="Reason for the time change")


class BatchUpdateScheduleArgs(PydanticBaseModel):
    """Schema for batch schedule updates via agent."""

    updates: list[ScheduleConflictResolution] = Field(
        ..., description="List of schedule updates to apply")
    timezone: str | None = Field(None, description="Timezone for date parsing")
    confirm: bool = Field(
        default=False, description="Set to true to confirm and apply the changes")


class DeleteTodoArgs(PydanticBaseModel):
    """Schema for deleting a todo via agent."""

    todo_id: str = Field(...,
                         description="The UUID of the todo item to delete.")


class UpdateTodoArgs(PydanticBaseModel):
    """Schema for updating a todo via agent."""

    todo_id: str = Field(...,
                         description="The UUID of the todo item to update")
    item: str | None = Field(
        None, description="The new name/title of the todo item")
    description: str | None = Field(
        None, description="The new description/content of the todo item")
    alarm_time: str | None = Field(
        None,
        description="The new planned date/time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified"
    )
    start_time: str | None = Field(
        None,
        description="The new start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD"
    )
    end_time: str | None = Field(
        None,
        description="The new end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD"
    )
    importance: str | None = Field(
        None, description="The new importance level: none, low, medium, high")
    timezone: str | None = Field(
        None,
        description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )


class GetTodoListArgs(PydanticBaseModel):
    """Schema for getting todo list via agent."""

    limit: int = Field(
        default=20, description="Maximum number of todos to return (default: 20)")
    from_date: str | None = Field(
        None, description="Filter todos from this date (YYYY-MM-DD)")
    to_date: str | None = Field(
        None, description="Filter todos to this date (YYYY-MM-DD)")
    importance: str | None = Field(
        None, description="Filter by importance level: none, low, medium, high")
    timezone: str | None = Field(
        None,
        description="Timezone for date filtering (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )


class SearchTodoArgs(PydanticBaseModel):
    """Schema for searching todos via agent."""

    query: str | None = Field(
        None, description="Search term to find in todo items or descriptions")
    importance: str | None = Field(
        None, description="Filter by importance level: none, low, medium, high")
    from_date: str | None = Field(
        None, description="Filter todos from this date (YYYY-MM-DD)")
    to_date: str | None = Field(
        None, description="Filter todos to this date (YYYY-MM-DD)")
    limit: int = Field(
        default=10, description="Maximum number of results to return")
    timezone: str | None = Field(
        None,
        description="Timezone for date filtering (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
