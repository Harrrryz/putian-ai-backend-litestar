"""Todo agent tools and helper implementations.

This module was extracted from the `app.domain.todo.todo_agents` implementation
so that the simplified `todo_agents` domain can reuse the richer toolset
without duplicating code.

It provides:
 - Pydantic argument models for each tool
 - Implementation functions (create, delete, update, list, analyze, schedule, batch update)
 - Helper utilities for scheduling and conflict detection
 - FunctionTool instances wired to the implementations
 - `get_todo_agent()` factory returning an Agent with all tools attached
 - `set_agent_context()` to inject per-request service instances & current user

The `TodoAgentService` in this domain should call `set_agent_context()` before
invoking the agent so the tool implementations can access services.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agents import (
    Agent,
    FunctionTool,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    Runner,
)
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config.base import get_settings
from app.db import models as m
from app.db.models.importance import Importance
from app.db.models.todo import Todo

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from app.domain.todo.services import TodoService, TagService

# ---------------------------------------------------------------------------
# Argument models
# ---------------------------------------------------------------------------


class CreateTodoArgs(BaseModel):
    item: str = Field(...,
                      description="The name/title of the todo item to create")
    description: str | None = Field(
        default=None, description="The description/content of the todo item")
    alarm_time: str | None = Field(
        default=None,
        description="The alarm time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified",
    )
    start_time: str = Field(
        ..., description="The start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    end_time: str = Field(
        ..., description="The end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    tags: list[str] | None = Field(
        default=None, description="List of tag names to associate with the todo. Common tags: 'work', 'personal', 'study', 'entertainment'"
    )
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
    auto_schedule: bool = Field(
        default=False, description="Whether to automatically schedule this todo if no specific time is provided"
    )


class ScheduleTodoArgs(BaseModel):
    item: str = Field(...,
                      description="The name/title of the todo item to schedule")
    description: str | None = Field(
        default=None, description="The description/content of the todo item")
    target_date: str | None = Field(
        default=None, description="The target date for scheduling (YYYY-MM-DD). If not provided, defaults to today or tomorrow"
    )
    duration_minutes: int = Field(
        default=60, description="Estimated duration of the task in minutes (default: 60)")
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
    preferred_time_of_day: str | None = Field(
        default=None, description="Preferred time of day: 'morning' (8-12), 'afternoon' (12-17), 'evening' (17-21), or specific time range"
    )
    tags: list[str] | None = Field(
        default=None, description="List of tag names to associate with the todo")


class AnalyzeScheduleArgs(BaseModel):
    target_date: str | None = Field(
        default=None, description="The date to analyze (YYYY-MM-DD). If not provided, analyzes today and tomorrow"
    )
    timezone: str | None = Field(
        default=None, description="Timezone for date analysis (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )
    include_days: int = Field(
        default=3, description="Number of days to analyze starting from target_date (default: 3)")


class ScheduleConflictResolution(BaseModel):
    todo_id: str = Field(..., description="The UUID of the todo to reschedule")
    new_time: str = Field(...,
                          description="New time in format YYYY-MM-DD HH:MM:SS")
    reason: str = Field(..., description="Reason for the time change")


class BatchUpdateScheduleArgs(BaseModel):
    updates: list[ScheduleConflictResolution] = Field(
        ..., description="List of schedule updates to apply")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing")
    confirm: bool = Field(
        default=False, description="Set to true to confirm and apply the changes")


class DeleteTodoArgs(BaseModel):
    todo_id: str = Field(...,
                         description="The UUID of the todo item to delete.")


class UpdateTodoArgs(BaseModel):
    todo_id: str = Field(...,
                         description="The UUID of the todo item to update")
    item: str | None = Field(
        default=None, description="The new name/title of the todo item")
    description: str | None = Field(
        default=None, description="The new description/content of the todo item")
    alarm_time: str | None = Field(
        default=None, description="The new planned date/time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified"
    )
    start_time: str | None = Field(
        default=None, description="The new start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    end_time: str | None = Field(
        default=None, description="The new end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    importance: str | None = Field(
        default=None, description="The new importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )


class GetTodoListArgs(BaseModel):
    limit: int = Field(
        default=20, description="Maximum number of todos to return (default: 20)")
    from_date: str | None = Field(
        default=None, description="Filter todos from this date (YYYY-MM-DD)")
    to_date: str | None = Field(
        default=None, description="Filter todos to this date (YYYY-MM-DD)")
    importance: str | None = Field(
        default=None, description="Filter by importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date filtering (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )


class SearchTodoArgs(BaseModel):
    query: str | None = Field(
        default=None, description="Search term to find in todo items or descriptions")
    importance: str | None = Field(
        default=None, description="Filter by importance level: none, low, medium, high")
    from_date: str | None = Field(
        default=None, description="Filter todos from this date (YYYY-MM-DD)")
    to_date: str | None = Field(
        default=None, description="Filter todos to this date (YYYY-MM-DD)")
    limit: int = Field(
        default=10, description="Maximum number of results to return")
    timezone: str | None = Field(
        default=None, description="Timezone for date filtering (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used."
    )


# ---------------------------------------------------------------------------
# Global context for tool implementations (set per user/session)
# ---------------------------------------------------------------------------
_todo_service: TodoService | None = None
_tag_service: TagService | None = None
_current_user_id: UUID | None = None


def set_agent_context(todo_service: TodoService, tag_service: TagService, user_id: UUID) -> None:
    """Inject services & user context for subsequent tool calls."""
    global _todo_service, _tag_service, _current_user_id
    _todo_service = todo_service
    _tag_service = tag_service
    _current_user_id = user_id


# ---------------------------------------------------------------------------
# Tool implementation helpers & functions
# (Copied / adapted from original todo domain implementation)
# ---------------------------------------------------------------------------


async def delete_todo_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401 - concise reuse
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    try:
        parsed = DeleteTodoArgs.model_validate_json(args)
    except ValueError:
        return f"Error: Invalid todo ID '{args}'"
    try:
        todo_uuid = UUID(parsed.todo_id)
        todo = await _todo_service.get(todo_uuid)
        if not todo:
            return f"Todo item with ID {parsed.todo_id} not found."
        if todo.user_id != _current_user_id:
            return f"Todo item with ID {parsed.todo_id} does not belong to you."
        await _todo_service.delete(todo_uuid)
        return f"Successfully deleted todo '{todo.item}' (ID: {parsed.todo_id})"
    except ValueError:
        return f"Error: Invalid UUID format '{parsed.todo_id}'"
    except Exception as e:  # pragma: no cover - defensive
        return f"Error deleting todo: {e!s}"


async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401
    if not _todo_service or not _tag_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    parsed = CreateTodoArgs.model_validate_json(args)
    user_tz = ZoneInfo(parsed.timezone) if parsed.timezone else UTC
    # alarm_time
    alarm_time_obj = None
    if parsed.alarm_time:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                alarm_time_obj = datetime.strptime(
                    parsed.alarm_time, fmt).replace(tzinfo=user_tz).astimezone(UTC)
                break
            except ValueError:
                continue
        if alarm_time_obj is None:
            return f"Error: Invalid alarm time format '{parsed.alarm_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
    # start
    start_time_obj = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            start_time_obj = datetime.strptime(
                parsed.start_time, fmt).replace(tzinfo=user_tz).astimezone(UTC)
            break
        except ValueError:
            continue
    if start_time_obj is None:
        return f"Error: Invalid start time format '{parsed.start_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
    # end
    end_time_obj = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            end_time_obj = datetime.strptime(parsed.end_time, fmt).replace(
                tzinfo=user_tz).astimezone(UTC)
            break
        except ValueError:
            continue
    if end_time_obj is None:
        return f"Error: Invalid end time format '{parsed.end_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
    if end_time_obj <= start_time_obj:  # type: ignore[arg-type]
        return "Error: End time must be after start time"
    try:
        # type: ignore[arg-type]
        conflicts = await _todo_service.check_time_conflict(_current_user_id, start_time_obj, end_time_obj)
        if conflicts:
            user_tz_local = ZoneInfo(
                parsed.timezone) if parsed.timezone else UTC
            details = []
            for c in conflicts:
                details.append(
                    f"• '{c.item}' ({c.start_time.astimezone(user_tz_local).strftime('%Y-%m-%d %H:%M')} - {c.end_time.astimezone(user_tz_local).strftime('%Y-%m-%d %H:%M')})"
                )
            return (
                "❌ Time conflict detected! The requested time slot conflicts with existing todos:\n"
                + "\n".join(details)
                + "\n\nPlease choose a different time or use the schedule_todo tool to find an available slot."
            )
    except Exception as e:  # pragma: no cover
        return f"Error checking for time conflicts: {e!s}"
    try:
        importance_enum = Importance(parsed.importance.lower())
    except ValueError:
        importance_enum = Importance.NONE
    todo_data: dict[str, object] = {
        "item": parsed.item,
        "description": parsed.description,
        "importance": importance_enum,
        "start_time": start_time_obj,
        "end_time": end_time_obj,
        "user_id": _current_user_id,
    }
    if alarm_time_obj is not None:
        todo_data["alarm_time"] = alarm_time_obj
    try:
        todo = await _todo_service.create(todo_data)
    except Exception as e:  # pragma: no cover
        return f"Error creating todo: {e!s}"
    tag_info = f" (tags: {', '.join(parsed.tags)})" if parsed.tags else ""
    start_str = start_time_obj.astimezone(user_tz).strftime(
        "%Y-%m-%d %H:%M")  # type: ignore[union-attr]
    end_str = end_time_obj.astimezone(user_tz).strftime(
        "%Y-%m-%d %H:%M")  # type: ignore[union-attr]
    return f"Successfully created todo '{todo.item}' (ID: {todo.id}) scheduled from {start_str} to {end_str}{tag_info}"


async def update_todo_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    try:
        parsed = UpdateTodoArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"
    try:
        todo_uuid = UUID(parsed.todo_id)
        todo = await _todo_service.get_todo_by_id(todo_uuid, _current_user_id)
        if not todo:
            return f"Todo item with ID {parsed.todo_id} not found."
    except ValueError:
        return f"Error: Invalid UUID format '{parsed.todo_id}'"
    except Exception as e:  # pragma: no cover
        return f"Error finding todo: {e!s}"
    update_data: dict[str, object] = {}
    user_tz = UTC
    if parsed.timezone:
        try:
            user_tz = ZoneInfo(parsed.timezone)
        except Exception:
            return (
                f"Error: Invalid timezone '{parsed.timezone}'. Use a valid timezone name like 'America/New_York' or 'Asia/Shanghai'"
            )
    if parsed.item is not None:
        update_data["item"] = parsed.item
    if parsed.description is not None:
        update_data["description"] = parsed.description
    if parsed.alarm_time is not None:
        parsed_ok = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed_ok = datetime.strptime(
                    parsed.alarm_time, fmt).replace(tzinfo=user_tz)
                break
            except ValueError:
                continue
        if parsed_ok is None:
            return f"Error: Invalid date format '{parsed.alarm_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
        update_data["alarm_time"] = parsed_ok.astimezone(UTC)
    if parsed.importance is not None:
        try:
            update_data["importance"] = Importance(parsed.importance.lower())
        except ValueError:
            return f"Error: Invalid importance level '{parsed.importance}'. Use: none, low, medium, high"
    if parsed.start_time is not None:
        start_ok = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                start_ok = datetime.strptime(
                    parsed.start_time, fmt).replace(tzinfo=user_tz)
                break
            except ValueError:
                continue
        if start_ok is None:
            return f"Error: Invalid start time format '{parsed.start_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
        update_data["start_time"] = start_ok.astimezone(UTC)
    if parsed.end_time is not None:
        end_ok = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                end_ok = datetime.strptime(
                    parsed.end_time, fmt).replace(tzinfo=user_tz)
                break
            except ValueError:
                continue
        if end_ok is None:
            return f"Error: Invalid end time format '{parsed.end_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
        update_data["end_time"] = end_ok.astimezone(UTC)
    # validate ordering
    if "start_time" in update_data and "end_time" in update_data:
        if update_data["end_time"] <= update_data["start_time"]:  # type: ignore[operator]
            return "Error: End time must be after start time"
    elif "start_time" in update_data and todo.end_time:
        # type: ignore[operator]
        if todo.end_time <= update_data["start_time"]:
            return "Error: New start time must be before existing end time"
    elif "end_time" in update_data and todo.start_time:
        if update_data["end_time"] <= todo.start_time:  # type: ignore[operator]
            return "Error: New end time must be after existing start time"
    if "start_time" in update_data or "end_time" in update_data:
        final_start = update_data.get("start_time", todo.start_time)
        final_end = update_data.get("end_time", todo.end_time)
        if isinstance(final_start, datetime) and isinstance(final_end, datetime):
            try:
                conflicts = await _todo_service.check_time_conflict(
                    _current_user_id, final_start, final_end, todo.id
                )
                if conflicts:
                    details = []
                    for c in conflicts:
                        details.append(
                            f"• '{c.item}' ({c.start_time.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')} - {c.end_time.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')})"
                        )
                    return (
                        "❌ Time conflict detected! The updated time slot conflicts with existing todos:\n"
                        + "\n".join(details)
                        + "\n\nPlease choose a different time."
                    )
            except Exception as e:  # pragma: no cover
                return f"Error checking for time conflicts: {e!s}"
    try:
        updated_fields = []
        for field, value in update_data.items():
            setattr(todo, field, value)
            updated_fields.append(field)
        updated = await _todo_service.update(todo)
        return f"Successfully updated todo '{updated.item}' (ID: {updated.id}). Updated fields: {', '.join(updated_fields)}"
    except Exception as e:  # pragma: no cover
        return f"Error updating todo: {e!s}"


async def get_todo_list_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    try:
        parsed = GetTodoListArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"
    filters = [m.Todo.user_id == _current_user_id]
    user_tz = UTC
    if parsed.timezone:
        try:
            user_tz = ZoneInfo(parsed.timezone)
        except Exception:
            return f"Error: Invalid timezone '{parsed.timezone}'. Use a valid timezone name like 'America/New_York' or 'Asia/Shanghai'"
    if parsed.from_date:
        try:
            from_obj = datetime.strptime(
                parsed.from_date, "%Y-%m-%d").replace(tzinfo=user_tz)
            filters.append(m.Todo.alarm_time >= from_obj.astimezone(UTC))
        except ValueError:
            return f"Error: Invalid from_date format '{parsed.from_date}'. Use YYYY-MM-DD"
    if parsed.to_date:
        try:
            to_obj = datetime.strptime(
                parsed.to_date, "%Y-%m-%d").replace(tzinfo=user_tz, hour=23, minute=59, second=59)
            filters.append(m.Todo.alarm_time <= to_obj.astimezone(UTC))
        except ValueError:
            return f"Error: Invalid to_date format '{parsed.to_date}'. Use YYYY-MM-DD"
    if parsed.importance:
        try:
            filters.append(m.Todo.importance == Importance(
                parsed.importance.lower()))
        except ValueError:
            return f"Error: Invalid importance level '{parsed.importance}'. Use: none, low, medium, high"
    try:
        from advanced_alchemy.filters import LimitOffset
        todos, total = await _todo_service.list_and_count(*filters, LimitOffset(limit=parsed.limit, offset=0))
        if not todos:
            parts = []
            if parsed.from_date:
                parts.append(f"from {parsed.from_date}")
            if parsed.to_date:
                parts.append(f"to {parsed.to_date}")
            if parsed.importance:
                parts.append(f"importance: {parsed.importance}")
            return f"No todos found{(' with filters: ' + ', '.join(parts)) if parts else ''}."
        results = []
        for t in todos:
            if t.alarm_time:
                at_local = t.alarm_time.astimezone(user_tz)
                alarm_str = at_local.strftime(
                    "%Y-%m-%d %H:%M:%S") + (f" ({at_local.tzinfo})" if user_tz != UTC else "")
            else:
                alarm_str = "No plan time"
            results.append(
                f"• {t.item} (ID: {t.id})\n  Description: {t.description or 'No description'}\n  Plan time: {alarm_str}\n  Importance: {t.importance.value}"
            )
        filter_parts = []
        if parsed.from_date:
            filter_parts.append(f"from {parsed.from_date}")
        if parsed.to_date:
            filter_parts.append(f"to {parsed.to_date}")
        if parsed.importance:
            filter_parts.append(f"importance: {parsed.importance}")
        if parsed.timezone:
            filter_parts.append(f"timezone: {parsed.timezone}")
        filter_text = f" with filters: {', '.join(filter_parts)}" if filter_parts else ""
        return (
            f"Your todos{filter_text} (showing {min(len(todos), parsed.limit)} of {total} total):\n\n"
            + "\n\n".join(results)
        )
    except Exception as e:  # pragma: no cover
        return f"Error getting todo list: {e!s}"


async def analyze_schedule_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    try:
        parsed = AnalyzeScheduleArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"
    try:
        user_tz, start_date = _parse_timezone_and_date(
            parsed.timezone, parsed.target_date)
        todos = await _get_todos_for_date_range(start_date, parsed.include_days)
        analysis = _analyze_schedule_by_days(
            todos, start_date, parsed.include_days, user_tz)
        result = f"📊 Schedule Analysis ({parsed.include_days} days starting from {start_date.strftime('%Y-%m-%d')}):\n\n" + \
            "\n\n".join(analysis)
        if parsed.timezone and user_tz != UTC:
            result += f"\n\n🌍 Times shown in {parsed.timezone} timezone"
        return result
    except (ValueError, ZoneInfoNotFoundError) as e:
        return f"Error: {e!s}"
    except Exception as e:  # pragma: no cover
        return f"Error analyzing schedule: {e!s}"


def _parse_timezone_and_date(timezone_str: str | None, target_date_str: str | None) -> tuple[ZoneInfo, datetime]:
    user_tz = ZoneInfo("UTC")
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError as e:  # pragma: no cover
            raise ValueError(f"Invalid timezone '{timezone_str}'") from e
    if target_date_str:
        try:
            start_date = datetime.strptime(
                target_date_str, "%Y-%m-%d").replace(tzinfo=user_tz)
        except ValueError as e:  # pragma: no cover
            raise ValueError(
                f"Invalid target_date format '{target_date_str}'. Use YYYY-MM-DD") from e
    else:
        start_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
    return user_tz, start_date


async def _get_todos_for_date_range(start_date: datetime, include_days: int) -> Sequence[Todo]:
    end_date = start_date + timedelta(days=include_days)
    start_utc = start_date.astimezone(UTC)
    end_utc = end_date.astimezone(UTC)
    from advanced_alchemy.filters import LimitOffset
    filters = [m.Todo.user_id == _current_user_id,
               m.Todo.alarm_time >= start_utc, m.Todo.alarm_time <= end_utc]
    if not _todo_service:  # pragma: no cover
        raise RuntimeError("Todo service not initialized")
    todos, _ = await _todo_service.list_and_count(*filters, LimitOffset(limit=100, offset=0))
    return todos


def _analyze_schedule_by_days(todos: Sequence[Todo], start_date: datetime, include_days: int, user_tz: ZoneInfo) -> list[str]:
    analysis = []
    for offset in range(include_days):
        current = start_date + timedelta(days=offset)
        analysis.append(_analyze_single_day(todos, current, user_tz))
    return analysis


def _analyze_single_day(todos: Sequence[Todo], current_date: datetime, user_tz: ZoneInfo) -> str:
    day_start = current_date.replace(hour=0, minute=0, second=0)
    day_end = current_date.replace(hour=23, minute=59, second=59)
    day_start_utc = day_start.astimezone(UTC)
    day_end_utc = day_end.astimezone(UTC)
    day_todos = [t for t in todos if day_start_utc <=
                 t.alarm_time <= day_end_utc]  # type: ignore
    day_todos.sort(key=lambda x: x.alarm_time)  # type: ignore
    free_slots = _find_free_time_slots(day_todos, current_date, user_tz)
    day_str = current_date.strftime("%A, %B %d, %Y")
    result = f"📅 {day_str}:\n"
    if day_todos:
        result += "  Scheduled todos:\n"
        for t in day_todos:
            if t.alarm_time:
                local_time = t.alarm_time.astimezone(user_tz)
                result += f"    • {local_time.strftime('%H:%M')} - {t.item} (importance: {t.importance.value})\n"
    else:
        result += "  No scheduled todos\n"
    if free_slots:
        result += "  Available time slots:\n" + "\n".join(free_slots)
    else:
        result += "  ⚠️  No significant free time slots available"
    return result


def _find_free_time_slots(day_todos: list, current_date: datetime, user_tz: ZoneInfo) -> list[str]:
    work_start = current_date.replace(hour=8, minute=0)
    work_end = current_date.replace(hour=22, minute=0)
    if not day_todos:
        return [f"  🟢 {work_start.strftime('%H:%M')} - {work_end.strftime('%H:%M')} (14 hours available)"]
    free = []
    current_time = work_start
    for todo in day_todos:
        todo_time_local = todo.alarm_time.astimezone(user_tz)
        if current_time < todo_time_local:
            gap_hours = (todo_time_local - current_time).total_seconds() / 3600
            if gap_hours >= 0.5:
                free.append(
                    f"  🟢 {current_time.strftime('%H:%M')} - {todo_time_local.strftime('%H:%M')} ({gap_hours:.1f} hours available)"
                )
        current_time = max(current_time, todo_time_local + timedelta(hours=1))
    if current_time < work_end:
        gap_hours = (work_end - current_time).total_seconds() / 3600
        if gap_hours >= 0.5:
            free.append(
                f"  🟢 {current_time.strftime('%H:%M')} - {work_end.strftime('%H:%M')} ({gap_hours:.1f} hours available)"
            )
    return free


async def schedule_todo_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401
    if not _todo_service or not _tag_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    try:
        parsed = ScheduleTodoArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"
    try:
        user_tz, target_date = _determine_schedule_target_date(
            parsed.timezone, parsed.target_date)
        existing = await _get_existing_todos_for_day(target_date, user_tz)
        suggested = _find_optimal_time_slot(
            target_date, parsed, existing, user_tz)
        if not suggested:
            return _handle_no_available_slot(target_date, parsed, existing, user_tz)
        todo = await _create_scheduled_todo(parsed, suggested)
        return _format_scheduling_success(todo, suggested, user_tz)
    except (ValueError, ZoneInfoNotFoundError) as e:
        return f"Error: {e!s}"
    except Exception as e:  # pragma: no cover
        return f"Error scheduling todo: {e!s}"


def _determine_schedule_target_date(timezone_str: str | None, target_date_str: str | None) -> tuple[ZoneInfo, datetime]:
    user_tz = ZoneInfo("UTC")
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError as e:  # pragma: no cover
            raise ValueError(f"Invalid timezone '{timezone_str}'") from e
    if target_date_str:
        try:
            target_date = datetime.strptime(
                target_date_str, "%Y-%m-%d").replace(tzinfo=user_tz)
        except ValueError as e:  # pragma: no cover
            raise ValueError(
                f"Invalid target_date format '{target_date_str}'. Use YYYY-MM-DD") from e
        return user_tz, target_date
    now = datetime.now(user_tz)
    if now.hour >= 18:
        target_date = now.replace(
            hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        target_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return user_tz, target_date


async def _get_existing_todos_for_day(target_date: datetime, user_tz: ZoneInfo) -> list:
    day_start = target_date.replace(hour=0, minute=0, second=0)
    day_end = target_date.replace(hour=23, minute=59, second=59)
    day_start_utc = day_start.astimezone(UTC)
    day_end_utc = day_end.astimezone(UTC)
    from advanced_alchemy.filters import LimitOffset
    filters = [m.Todo.user_id == _current_user_id, m.Todo.start_time >=
               day_start_utc, m.Todo.start_time <= day_end_utc]
    if not _todo_service:  # pragma: no cover
        raise RuntimeError("Todo service not initialized")
    existing, _ = await _todo_service.list_and_count(*filters, LimitOffset(limit=50, offset=0))
    valid = [
        t for t in existing if t.start_time is not None and t.end_time is not None]
    valid.sort(key=lambda x: x.start_time)  # type: ignore
    return valid


def _find_optimal_time_slot(target_date: datetime, parsed: ScheduleTodoArgs, existing: list, user_tz: ZoneInfo) -> datetime | None:
    prefs = {"morning": (8, 12), "afternoon": (12, 17), "evening": (17, 21)}
    if parsed.preferred_time_of_day and parsed.preferred_time_of_day.lower() in prefs:
        s, e = prefs[parsed.preferred_time_of_day.lower()]
        slot = _find_free_slot(
            target_date, s, e, parsed.duration_minutes, existing, user_tz)
        if slot:
            return slot
    for period in ["morning", "afternoon", "evening"]:
        s, e = prefs[period]
        slot = _find_free_slot(
            target_date, s, e, parsed.duration_minutes, existing, user_tz)
        if slot:
            return slot
    return None


def _handle_no_available_slot(target_date: datetime, parsed: ScheduleTodoArgs, existing: list, user_tz: ZoneInfo) -> str:
    conflicts = _detect_scheduling_conflicts(
        target_date, parsed.duration_minutes, existing, user_tz)
    if conflicts:
        info = "\n".join(
            [f"  • {c['time']} - {c['item']} (importance: {c['importance']})" for c in conflicts])
        return (
            f"⚠️ No free time slots found for '{parsed.item}' on {target_date.strftime('%Y-%m-%d')}.\n\nExisting todos that might conflict:\n"
            f"{info}\n\nWould you like me to suggest rescheduling some todos to make room?"
        )
    return f"⚠️ No suitable time slots found for '{parsed.item}' on {target_date.strftime('%Y-%m-%d')}. The day appears to be fully booked."


async def _create_scheduled_todo(parsed: ScheduleTodoArgs, suggested_time: datetime) -> Todo:
    try:
        importance_enum = Importance(parsed.importance.lower())
    except ValueError:
        importance_enum = Importance.NONE
    duration_delta = timedelta(minutes=parsed.duration_minutes)
    end_time = suggested_time + duration_delta
    if not _todo_service or not _current_user_id:  # pragma: no cover
        raise RuntimeError("Todo service not initialized")
    conflicts = await _todo_service.check_time_conflict(
        _current_user_id, suggested_time.astimezone(
            UTC), end_time.astimezone(UTC)
    )
    if conflicts:
        details = [f"'{c.item}'" for c in conflicts]
        raise RuntimeError(
            f"Time conflict detected with: {', '.join(details)}")
    data = {
        "item": parsed.item,
        "description": parsed.description,
        "importance": importance_enum,
        "user_id": _current_user_id,
        "start_time": suggested_time.astimezone(UTC),
        "end_time": end_time.astimezone(UTC),
        "alarm_time": suggested_time.astimezone(UTC),
    }
    return await _todo_service.create(data)


def _format_scheduling_success(todo: Todo, suggested_time: datetime, user_tz: ZoneInfo) -> str:
    ts = suggested_time.strftime(
        "%Y-%m-%d %H:%M:%S") + (f" ({user_tz})" if user_tz != UTC else "")
    return f"✅ Successfully scheduled '{todo.item}' for {ts}\n\nThis time slot was chosen based on your existing schedule and preferences."


def _find_free_slot(target_date: datetime, start_hour: int, end_hour: int, duration_minutes: int, existing: list, user_tz: ZoneInfo) -> datetime | None:
    slot_start = target_date.replace(hour=start_hour, minute=0)
    slot_end = target_date.replace(hour=end_hour, minute=0)
    duration_delta = timedelta(minutes=duration_minutes)
    current = slot_start
    for todo in existing:
        if todo.start_time and todo.end_time:
            t_start = todo.start_time.astimezone(user_tz)
            t_end = todo.end_time.astimezone(user_tz)
        elif todo.alarm_time:
            t_start = todo.alarm_time.astimezone(user_tz)
            t_end = t_start + timedelta(hours=1)
        else:
            continue
        if current + duration_delta <= t_start:
            return current
        current = max(current, t_end)
    if current + duration_delta <= slot_end:
        return current
    return None


def _detect_scheduling_conflicts(target_date: datetime, duration_minutes: int, existing: list, user_tz: ZoneInfo) -> list:
    conflicts = []
    for todo in existing:
        todo_time_local = todo.alarm_time.astimezone(user_tz)
        conflicts.append({"time": todo_time_local.strftime(
            "%H:%M"), "item": todo.item, "importance": todo.importance.value})
    return conflicts


async def batch_update_schedule_impl(ctx: RunContextWrapper, args: str) -> str:  # noqa: D401
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"
    try:
        parsed = BatchUpdateScheduleArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"
    if not parsed.confirm:
        return _generate_update_preview(parsed)
    user_tz = _get_user_timezone(parsed.timezone)
    if isinstance(user_tz, str):
        return user_tz
    success, failed = await _apply_schedule_updates(parsed.updates, user_tz)
    return _format_update_results(success, failed)


def _generate_update_preview(parsed: BatchUpdateScheduleArgs) -> str:
    preview = "📋 Proposed Schedule Changes:\n\n"
    for i, upd in enumerate(parsed.updates, 1):
        preview += f"{i}. Todo ID ending in ...{upd.todo_id[-8:]}:\n   New time: {upd.new_time}\n   Reason: {upd.reason}\n\n"
    preview += "⚠️  To confirm these changes, set 'confirm: true' in your request."
    return preview


def _get_user_timezone(timezone_str: str | None) -> ZoneInfo | str:
    user_tz = ZoneInfo("UTC")
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError:
            return f"Error: Invalid timezone '{timezone_str}'"
    return user_tz


async def _apply_schedule_updates(updates: list, user_tz: ZoneInfo) -> tuple[list[str], list[str]]:
    success, failed = [], []
    for upd in updates:
        try:
            todo_uuid = UUID(upd.todo_id)
            if not _todo_service or not _current_user_id:
                raise RuntimeError("Todo service not initialized")
            todo = await _todo_service.get_todo_by_id(todo_uuid, _current_user_id)
            if not todo:
                failed.append(f"Todo {upd.todo_id} not found")
                continue
            try:
                new_time_obj = datetime.strptime(
                    upd.new_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)
            except ValueError:
                failed.append(
                    f"Invalid time format for todo {upd.todo_id}: {upd.new_time}")
                continue
            todo.alarm_time = new_time_obj.astimezone(UTC)
            await _todo_service.update(todo)
            success.append(f"✅ '{todo.item}' rescheduled to {upd.new_time}")
        except Exception as e:  # pragma: no cover
            failed.append(f"Error updating todo {upd.todo_id}: {e!s}")
    return success, failed


def _format_update_results(successful: list[str], failed: list[str]) -> str:
    result = "📅 Schedule Update Results:\n\n"
    if successful:
        result += "Successful updates:\n" + "\n".join(successful) + "\n\n"
    if failed:
        result += "Failed updates:\n" + "\n".join(failed)
    return result


# ---------------------------------------------------------------------------
# Agent & tools
# ---------------------------------------------------------------------------

TODO_SYSTEM_INSTRUCTIONS = f"""You are a helpful todo list assistant with intelligent scheduling capabilities and automatic time conflict detection. You can create, delete, update, search todo items, and automatically schedule them based on the user's existing calendar while preventing time conflicts.

When creating todos:
- Extract the main task as the 'item' (title)
- Use any additional details as 'description'
- REQUIRED: Parse and include 'start_time' and 'end_time' (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD) - these are mandatory fields
- Optional: Parse 'alarm_time' if mentioned (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD) for reminders/notifications
- Ensure end_time is always after start_time
- AUTOMATIC CONFLICT DETECTION: The system will automatically check for time conflicts with existing todos and prevent overlapping schedules
- If conflicts are detected, inform the user about conflicting todos and suggest alternative times
- If the user only provide start_time and duration, calculate end_time based on the duration (default: 60 minutes)
- If auto_schedule is true and no specific times are provided, use the schedule_todo tool to find optimal time slots
- Assign appropriate importance: none (default), low, medium, high
- Suggest relevant tags like: 'work', 'personal', 'study', 'shopping', 'health', 'entertainment'
- Support timezone parameter for proper date parsing (e.g., 'America/New_York', 'Asia/Shanghai')
- Do not return the ID of the user and todo items.

When deleting todos:
- Use the get_todo_list tool first to show the user their current todos
- Ask the user to specify which todo they want to delete by providing the todo ID
- Only delete todos by their UUID ID, not by title or description
- Confirm successful deletion with the todo title
- Do not return the ID of the user and todo items.

When updating todos:
- Require the todo ID (UUID) to identify which todo to update
- Only update the fields that the user wants to change
- Parse dates/times if mentioned for 'start_time', 'end_time', or 'alarm_time' (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
- AUTOMATIC CONFLICT DETECTION: If start_time or end_time is being updated, the system will check for conflicts with other todos
- If conflicts are detected during updates, inform the user and suggest alternative times
- Ensure that if both start_time and end_time are updated, end_time is after start_time
- Support timezone parameter for proper date parsing (e.g., 'America/New_York', 'Asia/Shanghai')
- If no timezone is specified, UTC is used for date parsing
- Validate importance levels: none, low, medium, high
- Do not return the ID of the user and todo items.

When listing todos:
- Use the get_todo_list tool to show all todos for the current user
- Support filtering by date range (from_date, to_date) and importance level
- Support timezone parameter for proper date filtering and display (e.g., 'America/New_York', 'Asia/Shanghai')
- If no timezone is specified, UTC is used for filtering and display
- Display results with title, description, start time, end time, alarm time (if set), and importance
- All times are shown in the user's specified timezone (or UTC if not specified)
- Limit results to avoid overwhelming output (default 20)
- Show applied filters in the response for clarity
- Do not return the ID of the user and todo items.

Intelligent Scheduling Capabilities with Conflict Prevention:
- Use analyze_schedule tool to show the user their schedule and identify free time slots based on start_time and end_time
- Use schedule_todo tool when the user wants to create a todo without specifying exact times
- CONFLICT-FREE SCHEDULING: All scheduling functions automatically avoid time conflicts by checking against existing todos
- Prefer user's time preferences (morning, afternoon, evening) when scheduling
- Consider estimated duration when finding time slots
- Use batch_update_schedule tool when rescheduling multiple todos to resolve conflicts
- Always show proposed changes before applying batch updates (confirm: false first)
- Apply timezone awareness throughout all scheduling operations
- Schedule analysis considers the actual duration of todos (end_time - start_time)

Schedule Analysis:
- Analyze schedules for specific date ranges (default: 3 days starting today)
- Show existing todos with their start times, end times, and importance levels
- Identify free time slots between scheduled todos (8 AM and 10 PM working hours)
- Highlight conflicts and suggest optimal scheduling times
- Support different timezones for international users
- Consider actual todo durations when finding available slots

Auto-Scheduling Logic with Conflict Prevention:
- When creating todos without specific times, automatically find optimal slots based on duration
- GUARANTEED CONFLICT-FREE: All auto-scheduling respects existing todo time slots
- Consider user preferences for time of day (morning/afternoon/evening)
- Estimate task duration (default: 60 minutes) and find adequate time slots that don't overlap
- Avoid scheduling conflicts with existing todos by checking start_time and end_time
- Suggest rescheduling existing todos if no free slots are available
- Ensure proper time gaps between consecutive todos

Conflict Resolution:
- Detect scheduling conflicts when adding new todos or updating existing ones
- Propose solutions such as rescheduling lower-priority items
- Use batch update operations to efficiently resolve multiple conflicts
- Always require user confirmation before making schedule changes
- Provide clear information about conflicting todos including their time slots

If the user's input is unclear, ask for clarification. Always be helpful and ensure a smooth user experience. When you return the results, do not include any sensitive information or personal data, and do not return the UUID of the user and todo items. The system automatically prevents time conflicts, ensuring users never have overlapping todo schedules.

Today's date is {datetime.now(tz=UTC).strftime('%Y-%m-%d')}."""


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


def get_todo_agent() -> Agent:
    """Create and return a configured todo agent with all tools."""
    settings = get_settings()
    model = OpenAIChatCompletionsModel(
        model="doubao-1.5-pro-32k-250115",
        openai_client=AsyncOpenAI(
            api_key=settings.ai.VOLCENGINE_API_KEY, base_url=settings.ai.VOLCENGINE_BASE_URL
        ),
    )
    return Agent(
        name="TodoAssistant",
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=[
            create_todo_tool,
            delete_todo_tool,
            update_todo_tool,
            get_todo_list_tool,
            analyze_schedule_tool,
            schedule_todo_tool,
            batch_update_schedule_tool,
        ],
    )


__all__ = [  # noqa: RUF022
    "set_agent_context",
    "TODO_SYSTEM_INSTRUCTIONS",
    "get_todo_agent",
    "create_todo_tool",
    "delete_todo_tool",
    "update_todo_tool",
    "get_todo_list_tool",
    "analyze_schedule_tool",
    "schedule_todo_tool",
    "batch_update_schedule_tool",
]
