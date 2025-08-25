from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agents import Agent, FunctionTool, OpenAIChatCompletionsModel, RunContextWrapper, Runner
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.config.base import get_settings
from app.db import models as m
from app.db.models.importance import Importance
from app.db.models.todo import Todo
from app.domain.agent_sessions.services import AgentSessionService, SessionMessageService
from app.domain.todo.services import TagService, TodoService
from app.lib.database_session import DatabaseSession


class CreateTodoArgs(BaseModel):
    item: str = Field(...,
                      description="The name/title of the todo item to create")
    description: str | None = Field(
        default=None, description="The description/content of the todo item")
    alarm_time: str | None = Field(
        default=None, description="The alarm time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified")
    start_time: str = Field(...,
                            description="The start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    end_time: str = Field(...,
                          description="The end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    tags: list[str] | None = Field(
        default=None, description="List of tag names to associate with the todo. Common tags: 'work', 'personal', 'study', 'entertainment'")
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used.")
    auto_schedule: bool = Field(
        default=False, description="Whether to automatically schedule this todo if no specific time is provided")


class ScheduleTodoArgs(BaseModel):
    item: str = Field(...,
                      description="The name/title of the todo item to schedule")
    description: str | None = Field(
        default=None, description="The description/content of the todo item")
    target_date: str | None = Field(
        default=None, description="The target date for scheduling (YYYY-MM-DD). If not provided, defaults to today or tomorrow")
    duration_minutes: int = Field(
        default=60, description="Estimated duration of the task in minutes (default: 60)")
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used.")
    preferred_time_of_day: str | None = Field(
        default=None, description="Preferred time of day: 'morning' (8-12), 'afternoon' (12-17), 'evening' (17-21), or specific time range")
    tags: list[str] | None = Field(
        default=None, description="List of tag names to associate with the todo")


class AnalyzeScheduleArgs(BaseModel):
    target_date: str | None = Field(
        default=None, description="The date to analyze (YYYY-MM-DD). If not provided, analyzes today and tomorrow")
    timezone: str | None = Field(
        default=None, description="Timezone for date analysis (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used.")
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
    todo_id: str = Field(
        ...,
        description="The UUID of the todo item to delete."
    )


class UpdateTodoArgs(BaseModel):
    todo_id: str = Field(...,
                         description="The UUID of the todo item to update")
    item: str | None = Field(
        default=None, description="The new name/title of the todo item")
    description: str | None = Field(
        default=None, description="The new description/content of the todo item")
    alarm_time: str | None = Field(
        default=None, description="The new planned date/time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified")
    start_time: str | None = Field(
        default=None, description="The new start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    end_time: str | None = Field(
        default=None, description="The new end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    importance: str | None = Field(
        default=None, description="The new importance level: none, low, medium, high")
    timezone: str | None = Field(
        default=None, description="Timezone for date parsing (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used.")


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
        default=None, description="Timezone for date filtering (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used.")


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
        default=None, description="Timezone for date filtering (e.g., 'America/New_York', 'Asia/Shanghai'). If not provided, UTC is used.")


# Global variables to hold services and user context
_todo_service: TodoService | None = None
_tag_service: TagService | None = None
_current_user_id: UUID | None = None


def set_agent_context(todo_service: TodoService, tag_service: TagService, user_id: UUID) -> None:
    """Set the services and user context for the agent."""
    global _todo_service, _tag_service, _current_user_id
    _todo_service = todo_service
    _tag_service = tag_service
    _current_user_id = user_id


async def delete_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the delete_todo function."""
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    # Parse the arguments
    try:
        parsed_args = DeleteTodoArgs.model_validate_json(args)
        todo_id = parsed_args.todo_id
    except ValueError:
        return f"Error: Invalid todo ID '{args}'"

    # Get the todo item to verify it exists and belongs to the user
    try:
        todo_uuid = UUID(todo_id)
        todo = await _todo_service.get(todo_uuid)
        if not todo:
            return f"Todo item with ID {todo_id} not found."

        # Verify the todo belongs to the current user
        if todo.user_id != _current_user_id:
            return f"Todo item with ID {todo_id} does not belong to you."

        # Delete the todo item
        await _todo_service.delete(todo_uuid)
        return f"Successfully deleted todo '{todo.item}' (ID: {todo_id})"

    except ValueError:
        return f"Error: Invalid UUID format '{todo_id}'"
    except Exception as e:
        return f"Error deleting todo: {e!s}"


async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the create_todo function."""
    if not _todo_service or not _tag_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    # Parse the arguments
    parsed_args = CreateTodoArgs.model_validate_json(args)

    # Determine timezone to use
    user_tz = ZoneInfo(parsed_args.timezone) if parsed_args.timezone else UTC

    # Parse alarm_time if provided and convert to UTC
    alarm_time_obj = None
    if parsed_args.alarm_time:
        try:
            alarm_time_obj = datetime.strptime(
                parsed_args.alarm_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz).astimezone(UTC)
        except ValueError:
            try:
                alarm_time_obj = datetime.strptime(
                    parsed_args.alarm_time, "%Y-%m-%d").replace(tzinfo=user_tz).astimezone(UTC)
            except ValueError:
                return f"Error: Invalid alarm time format '{parsed_args.alarm_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

    # Parse start_time (required) and convert to UTC
    try:
        start_time_obj = datetime.strptime(
            parsed_args.start_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz).astimezone(UTC)
    except ValueError:
        try:
            start_time_obj = datetime.strptime(
                parsed_args.start_time, "%Y-%m-%d").replace(tzinfo=user_tz).astimezone(UTC)
        except ValueError:
            return f"Error: Invalid start time format '{parsed_args.start_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

    # Parse end_time (required) and convert to UTC
    try:
        end_time_obj = datetime.strptime(
            parsed_args.end_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz).astimezone(UTC)
    except ValueError:
        try:
            end_time_obj = datetime.strptime(
                parsed_args.end_time, "%Y-%m-%d").replace(tzinfo=user_tz).astimezone(UTC)
        except ValueError:
            return f"Error: Invalid end time format '{parsed_args.end_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

    # Validate that end_time is after start_time
    if end_time_obj <= start_time_obj:
        return "Error: End time must be after start time"

    # Check for time conflicts with existing todos
    try:
        conflicts = await _todo_service.check_time_conflict(
            _current_user_id, start_time_obj, end_time_obj
        )
        if conflicts:
            conflict_details = []
            for conflict in conflicts:
                conflict_start = conflict.start_time.astimezone(
                    user_tz).strftime("%Y-%m-%d %H:%M")
                conflict_end = conflict.end_time.astimezone(
                    user_tz).strftime("%Y-%m-%d %H:%M")
                conflict_details.append(
                    f"• '{conflict.item}' ({conflict_start} - {conflict_end})")

            conflict_list = "\n".join(conflict_details)
            return f"❌ Time conflict detected! The requested time slot conflicts with existing todos:\n{conflict_list}\n\nPlease choose a different time or use the schedule_todo tool to find an available slot."
    except Exception as e:
        return f"Error checking for time conflicts: {e!s}"

    # Convert importance string to enum
    try:
        importance_enum = Importance(parsed_args.importance.lower())
    except ValueError:
        importance_enum = Importance.NONE

    # Create todo data
    todo_data: dict[str, object] = {
        "item": parsed_args.item,
        "description": parsed_args.description,
        "importance": importance_enum,
        "start_time": start_time_obj,
        "end_time": end_time_obj,
        "user_id": _current_user_id,
    }

    # Only add alarm_time if it was provided
    if alarm_time_obj is not None:
        todo_data["alarm_time"] = alarm_time_obj

    # Create the todo
    try:
        print(todo_data)
        todo = await _todo_service.create(todo_data)
    except Exception as e:
        return f"Error creating todo: {e!s}"
    else:
        # Return success message with time info
        tag_info = f" (tags: {', '.join(parsed_args.tags)})" if parsed_args.tags else ""
        start_str = start_time_obj.astimezone(
            user_tz).strftime("%Y-%m-%d %H:%M")
        end_str = end_time_obj.astimezone(user_tz).strftime("%Y-%m-%d %H:%M")
        return f"Successfully created todo '{todo.item}' (ID: {todo.id}) scheduled from {start_str} to {end_str}{tag_info}"


async def update_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the update_todo function."""
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    # Parse the arguments
    try:
        parsed_args = UpdateTodoArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"

    # Get the todo item to update
    try:
        todo_uuid = UUID(parsed_args.todo_id)
        todo = await _todo_service.get_todo_by_id(todo_uuid, _current_user_id)
        if not todo:
            return f"Todo item with ID {parsed_args.todo_id} not found."
    except ValueError:
        return f"Error: Invalid UUID format '{parsed_args.todo_id}'"
    except Exception as e:
        return f"Error finding todo: {e!s}"

    # Prepare update data
    update_data: dict[str, object] = {}

    # Determine timezone to use for alarm_time parsing
    user_tz = UTC  # Default to UTC
    if parsed_args.timezone:
        try:
            user_tz = ZoneInfo(parsed_args.timezone)
        except Exception:
            return f"Error: Invalid timezone '{parsed_args.timezone}'. Use a valid timezone name like 'America/New_York' or 'Asia/Shanghai'"

    if parsed_args.item is not None:
        update_data["item"] = parsed_args.item

    if parsed_args.description is not None:
        update_data["description"] = parsed_args.description

    # Parse alarm_time if provided with timezone support
    if parsed_args.alarm_time is not None:
        try:
            # First try with full datetime format
            alarm_time_obj = datetime.strptime(
                parsed_args.alarm_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)
        except ValueError:
            try:
                # Then try with date only format (set to beginning of day)
                alarm_time_obj = datetime.strptime(
                    parsed_args.alarm_time, "%Y-%m-%d").replace(tzinfo=user_tz)
            except ValueError:
                return f"Error: Invalid date format '{parsed_args.alarm_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

        # Convert to UTC for database storage
        alarm_time_utc = alarm_time_obj.astimezone(UTC)
        update_data["alarm_time"] = alarm_time_utc

    # Convert importance string to enum if provided
    if parsed_args.importance is not None:
        try:
            importance_enum = Importance(parsed_args.importance.lower())
            update_data["importance"] = importance_enum
        except ValueError:
            return f"Error: Invalid importance level '{parsed_args.importance}'. Use: none, low, medium, high"

    # Parse start_time if provided with timezone support
    if parsed_args.start_time is not None:
        try:
            # First try with full datetime format
            start_time_obj = datetime.strptime(
                parsed_args.start_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)
        except ValueError:
            try:
                # Then try with date only format (set to beginning of day)
                start_time_obj = datetime.strptime(
                    parsed_args.start_time, "%Y-%m-%d").replace(tzinfo=user_tz)
            except ValueError:
                return f"Error: Invalid start time format '{parsed_args.start_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

        # Convert to UTC for database storage
        start_time_utc = start_time_obj.astimezone(UTC)
        update_data["start_time"] = start_time_utc

    # Parse end_time if provided with timezone support
    if parsed_args.end_time is not None:
        try:
            # First try with full datetime format
            end_time_obj = datetime.strptime(
                parsed_args.end_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)
        except ValueError:
            try:
                # Then try with date only format (set to end of day)
                end_time_obj = datetime.strptime(
                    parsed_args.end_time, "%Y-%m-%d").replace(tzinfo=user_tz)
            except ValueError:
                return f"Error: Invalid end time format '{parsed_args.end_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

        # Convert to UTC for database storage
        end_time_utc = end_time_obj.astimezone(UTC)
        update_data["end_time"] = end_time_utc

    # Validate that end_time is after start_time if both are being updated
    if "start_time" in update_data and "end_time" in update_data:
        start_time_val = update_data["start_time"]
        end_time_val = update_data["end_time"]
        if isinstance(start_time_val, datetime) and isinstance(end_time_val, datetime) and end_time_val <= start_time_val:
            return "Error: End time must be after start time"
    elif "start_time" in update_data and todo.end_time:
        start_time_val = update_data["start_time"]
        if isinstance(start_time_val, datetime) and isinstance(todo.end_time, datetime) and todo.end_time <= start_time_val:
            return "Error: New start time must be before existing end time"
    elif "end_time" in update_data and todo.start_time:
        end_time_val = update_data["end_time"]
        if isinstance(end_time_val, datetime) and isinstance(todo.start_time, datetime) and end_time_val <= todo.start_time:
            return "Error: New end time must be after existing start time"

    # Check for time conflicts if start_time or end_time is being updated
    if "start_time" in update_data or "end_time" in update_data:
        # Determine the final start and end times for conflict checking
        final_start_time = update_data.get("start_time", todo.start_time)
        final_end_time = update_data.get("end_time", todo.end_time)

        if isinstance(final_start_time, datetime) and isinstance(final_end_time, datetime):
            try:
                conflicts = await _todo_service.check_time_conflict(
                    _current_user_id, final_start_time, final_end_time, todo.id
                )
                if conflicts:
                    conflict_details = []
                    for conflict in conflicts:
                        conflict_start = conflict.start_time.astimezone(
                            user_tz).strftime("%Y-%m-%d %H:%M")
                        conflict_end = conflict.end_time.astimezone(
                            user_tz).strftime("%Y-%m-%d %H:%M")
                        conflict_details.append(
                            f"• '{conflict.item}' ({conflict_start} - {conflict_end})")

                    conflict_list = "\n".join(conflict_details)
                    return f"❌ Time conflict detected! The updated time slot conflicts with existing todos:\n{conflict_list}\n\nPlease choose a different time."
            except Exception as e:
                return f"Error checking for time conflicts: {e!s}"

    # Update the todo
    try:
        # Apply updates directly to the todo object
        updated_fields = []

        if "item" in update_data:
            todo.item = update_data["item"]  # type: ignore
            updated_fields.append("item")

        if "description" in update_data:
            todo.description = update_data["description"]  # type: ignore
            updated_fields.append("description")

        if "alarm_time" in update_data:
            todo.alarm_time = update_data["alarm_time"]  # type: ignore
            updated_fields.append("alarm_time")

        if "start_time" in update_data:
            todo.start_time = update_data["start_time"]  # type: ignore
            updated_fields.append("start_time")

        if "end_time" in update_data:
            todo.end_time = update_data["end_time"]  # type: ignore
            updated_fields.append("end_time")

        if "importance" in update_data:
            todo.importance = update_data["importance"]  # type: ignore
            updated_fields.append("importance")

        # Update the todo object in the database
        updated_todo = await _todo_service.update(todo)
        return f"Successfully updated todo '{updated_todo.item}' (ID: {updated_todo.id}). Updated fields: {', '.join(updated_fields)}"
    except Exception as e:
        return f"Error updating todo: {e!s}"


async def get_todo_list_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the get_todo_list function."""
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    # Parse the arguments
    try:
        parsed_args = GetTodoListArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"

    # Build filters
    filters = [m.Todo.user_id == _current_user_id]

    # Determine timezone to use
    user_tz = UTC  # Default to UTC
    if parsed_args.timezone:
        try:
            user_tz = ZoneInfo(parsed_args.timezone)
        except Exception:
            return f"Error: Invalid timezone '{parsed_args.timezone}'. Use a valid timezone name like 'America/New_York' or 'Asia/Shanghai'"

    # Date range filters for alarm_time
    if parsed_args.from_date:
        try:
            # Parse date in user's timezone and convert to UTC for database query
            from_date_obj = datetime.strptime(
                parsed_args.from_date, "%Y-%m-%d").replace(tzinfo=user_tz)
            from_date_utc = from_date_obj.astimezone(UTC)
            filters.append(m.Todo.alarm_time >= from_date_utc)
        except ValueError:
            return f"Error: Invalid from_date format '{parsed_args.from_date}'. Use YYYY-MM-DD"

    if parsed_args.to_date:
        try:
            # Parse date in user's timezone, set to end of day, and convert to UTC
            to_date_obj = datetime.strptime(
                parsed_args.to_date, "%Y-%m-%d").replace(tzinfo=user_tz, hour=23, minute=59, second=59)
            to_date_utc = to_date_obj.astimezone(UTC)
            filters.append(m.Todo.alarm_time <= to_date_utc)
        except ValueError:
            return f"Error: Invalid to_date format '{parsed_args.to_date}'. Use YYYY-MM-DD"

    # Importance filter
    if parsed_args.importance:
        try:
            importance_enum = Importance(parsed_args.importance.lower())
            filters.append(m.Todo.importance == importance_enum)
        except ValueError:
            return f"Error: Invalid importance level '{parsed_args.importance}'. Use: none, low, medium, high"

    # Get user's todos
    try:
        from advanced_alchemy.filters import LimitOffset
        limit_filter = LimitOffset(limit=parsed_args.limit, offset=0)
        todos, total = await _todo_service.list_and_count(*filters, limit_filter)

        if not todos:
            filter_info = []
            if parsed_args.from_date:
                filter_info.append(f"from {parsed_args.from_date}")
            if parsed_args.to_date:
                filter_info.append(f"to {parsed_args.to_date}")
            if parsed_args.importance:
                filter_info.append(f"importance: {parsed_args.importance}")

            filter_text = f" with filters: {', '.join(filter_info)}" if filter_info else ""
            return f"No todos found{filter_text}."

        # Format results
        results = []
        for todo in todos:
            if todo.alarm_time:
                # Convert UTC time from database to user's timezone for display
                alarm_time_in_user_tz = todo.alarm_time.astimezone(user_tz)
                alarm_time_str = alarm_time_in_user_tz.strftime(
                    "%Y-%m-%d %H:%M:%S")
                if user_tz != UTC:
                    # Show timezone info if not UTC
                    alarm_time_str += f" ({alarm_time_in_user_tz.tzinfo})"
            else:
                alarm_time_str = "No plan time"
            result = f"• {todo.item} (ID: {todo.id})\n  Description: {todo.description or 'No description'}\n  Plan time: {alarm_time_str}\n  Importance: {todo.importance.value}"
            results.append(result)

        filter_info = []
        if parsed_args.from_date:
            filter_info.append(f"from {parsed_args.from_date}")
        if parsed_args.to_date:
            filter_info.append(f"to {parsed_args.to_date}")
        if parsed_args.importance:
            filter_info.append(f"importance: {parsed_args.importance}")
        if parsed_args.timezone:
            filter_info.append(f"timezone: {parsed_args.timezone}")

        filter_text = f" with filters: {', '.join(filter_info)}" if filter_info else ""
        result_text = f"Your todos{filter_text} (showing {min(len(todos), parsed_args.limit)} of {total} total):\n\n" + \
            "\n\n".join(results)
        return result_text

    except Exception as e:
        return f"Error getting todo list: {e!s}"


async def analyze_schedule_impl(ctx: RunContextWrapper, args: str) -> str:
    """Analyze the user's schedule to identify free time slots and conflicts."""
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    try:
        parsed_args = AnalyzeScheduleArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"

    try:
        user_tz, start_date = _parse_timezone_and_date(
            parsed_args.timezone, parsed_args.target_date)
        todos = await _get_todos_for_date_range(start_date, parsed_args.include_days)
        schedule_analysis = _analyze_schedule_by_days(
            todos, start_date, parsed_args.include_days, user_tz)

        result = f"📊 Schedule Analysis ({parsed_args.include_days} days starting from {start_date.strftime('%Y-%m-%d')}):\n\n"
        result += "\n\n".join(schedule_analysis)

        if parsed_args.timezone and user_tz != UTC:
            result += f"\n\n🌍 Times shown in {parsed_args.timezone} timezone"

        return result
    except (ValueError, ZoneInfoNotFoundError) as e:
        return f"Error: {e!s}"
    except Exception as e:
        return f"Error analyzing schedule: {e!s}"


def _parse_timezone_and_date(timezone_str: str | None, target_date_str: str | None) -> tuple[ZoneInfo, datetime]:
    """Parse timezone and target date from input arguments."""
    user_tz = ZoneInfo("UTC")
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError as e:
            msg = f"Invalid timezone '{timezone_str}'"
            raise ValueError(msg) from e

    if target_date_str:
        try:
            start_date = datetime.strptime(
                target_date_str, "%Y-%m-%d").replace(tzinfo=user_tz)
        except ValueError as e:
            msg = f"Invalid target_date format '{target_date_str}'. Use YYYY-MM-DD"
            raise ValueError(msg) from e
    else:
        start_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)

    return user_tz, start_date


async def _get_todos_for_date_range(start_date: datetime, include_days: int) -> Sequence[Todo]:
    """Get todos for the specified date range."""
    end_date = start_date + timedelta(days=include_days)
    start_utc = start_date.astimezone(UTC)
    end_utc = end_date.astimezone(UTC)

    from advanced_alchemy.filters import LimitOffset
    filters = [
        m.Todo.user_id == _current_user_id,
        m.Todo.alarm_time >= start_utc,
        m.Todo.alarm_time <= end_utc
    ]
    if not _todo_service:
        raise RuntimeError("Todo service not initialized")
    todos, _ = await _todo_service.list_and_count(*filters, LimitOffset(limit=100, offset=0))
    return todos


def _analyze_schedule_by_days(todos: Sequence[Todo], start_date: datetime, include_days: int, user_tz: ZoneInfo) -> list[str]:
    """Analyze schedule day by day and return analysis for each day."""
    schedule_analysis = []
    for day_offset in range(include_days):
        current_date = start_date + timedelta(days=day_offset)
        day_analysis = _analyze_single_day(todos, current_date, user_tz)
        schedule_analysis.append(day_analysis)
    return schedule_analysis


def _analyze_single_day(todos: Sequence[Todo], current_date: datetime, user_tz: ZoneInfo) -> str:
    """Analyze a single day's schedule."""
    day_start = current_date.replace(hour=0, minute=0, second=0)
    day_end = current_date.replace(hour=23, minute=59, second=59)
    day_start_utc = day_start.astimezone(UTC)
    day_end_utc = day_end.astimezone(UTC)

    # Get todos for this day

    day_todos = [todo for todo in todos if day_start_utc <=
                 todo.alarm_time <= day_end_utc]  # type: ignore
    day_todos.sort(key=lambda x: x.alarm_time)  # type: ignore
    # Find free time slots
    free_slots = _find_free_time_slots(day_todos, current_date, user_tz)

    # Format day analysis
    day_str = current_date.strftime("%A, %B %d, %Y")
    day_analysis = f"📅 {day_str}:\n"

    if day_todos:
        day_analysis += "  Scheduled todos:\n"
        for todo in day_todos:
            if todo.alarm_time:
                # Convert UTC time from database to user's timezone for display
                todo_time_local = todo.alarm_time.astimezone(user_tz)
                day_analysis += f"    • {todo_time_local.strftime('%H:%M')} - {todo.item} (importance: {todo.importance.value})\n"
    else:
        day_analysis += "  No scheduled todos\n"

    if free_slots:
        day_analysis += "  Available time slots:\n" + "\n".join(free_slots)
    else:
        day_analysis += "  ⚠️  No significant free time slots available"

    return day_analysis


def _find_free_time_slots(day_todos: list, current_date: datetime, user_tz: ZoneInfo) -> list[str]:
    """Find free time slots in a day."""
    work_start = current_date.replace(hour=8, minute=0)
    work_end = current_date.replace(hour=22, minute=0)

    free_slots = []
    if not day_todos:
        # Entire day is free
        free_slots.append(
            f"  🟢 {work_start.strftime('%H:%M')} - {work_end.strftime('%H:%M')} (14 hours available)")
        return free_slots

    # Check for gaps between todos
    current_time = work_start
    for todo in day_todos:
        todo_time_local = todo.alarm_time.astimezone(user_tz)
        if current_time < todo_time_local:
            gap_hours = (todo_time_local - current_time).total_seconds() / 3600
            if gap_hours >= 0.5:  # At least 30 minutes
                free_slots.append(
                    f"  🟢 {current_time.strftime('%H:%M')} - {todo_time_local.strftime('%H:%M')} ({gap_hours:.1f} hours available)")

        # Assume each todo takes 1 hour if not specified
        current_time = max(current_time, todo_time_local +
                           timedelta(hours=1))

    # Check for time after last todo
    if current_time < work_end:
        gap_hours = (work_end - current_time).total_seconds() / 3600
        if gap_hours >= 0.5:
            free_slots.append(
                f"  🟢 {current_time.strftime('%H:%M')} - {work_end.strftime('%H:%M')} ({gap_hours:.1f} hours available)")

    return free_slots


async def schedule_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Intelligently schedule a todo by finding optimal time slots."""
    if not _todo_service or not _tag_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    try:
        parsed_args = ScheduleTodoArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"

    try:
        user_tz, target_date = _determine_schedule_target_date(
            parsed_args.timezone, parsed_args.target_date)
        existing_todos = await _get_existing_todos_for_day(target_date, user_tz)

        suggested_time = _find_optimal_time_slot(
            target_date, parsed_args, existing_todos, user_tz)

        if not suggested_time:
            return _handle_no_available_slot(target_date, parsed_args, existing_todos, user_tz)

        todo = await _create_scheduled_todo(parsed_args, suggested_time)
        return _format_scheduling_success(todo, suggested_time, user_tz)

    except (ValueError, ZoneInfoNotFoundError) as e:
        return f"Error: {e!s}"
    except Exception as e:
        return f"Error scheduling todo: {e!s}"


def _determine_schedule_target_date(timezone_str: str | None, target_date_str: str | None) -> tuple[ZoneInfo, datetime]:
    """Determine the target date and timezone for scheduling."""
    user_tz = ZoneInfo("UTC")
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError as e:
            msg = f"Invalid timezone '{timezone_str}'"
            raise ValueError(msg) from e

    if target_date_str:
        try:
            target_date = datetime.strptime(
                target_date_str, "%Y-%m-%d").replace(tzinfo=user_tz)
        except ValueError as e:
            msg = f"Invalid target_date format '{target_date_str}'. Use YYYY-MM-DD"
            raise ValueError(msg) from e
        return user_tz, target_date

    # Default to tomorrow if current time is after 6 PM, otherwise today
    now = datetime.now(user_tz)
    if now.hour >= 18:
        from datetime import timedelta
        target_date = now.replace(
            hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        target_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return user_tz, target_date


async def _get_existing_todos_for_day(target_date: datetime, user_tz: ZoneInfo) -> list:
    """Get existing todos for the target date."""
    day_start = target_date.replace(hour=0, minute=0, second=0)
    day_end = target_date.replace(hour=23, minute=59, second=59)
    day_start_utc = day_start.astimezone(UTC)
    day_end_utc = day_end.astimezone(UTC)

    from advanced_alchemy.filters import LimitOffset
    # Use start_time for scheduling-based queries
    filters = [
        m.Todo.user_id == _current_user_id,
        m.Todo.start_time >= day_start_utc,
        m.Todo.start_time <= day_end_utc
    ]
    if not _todo_service:
        msg = "Todo service not initialized"
        raise RuntimeError(msg)
    existing_todos, _ = await _todo_service.list_and_count(*filters, LimitOffset(limit=50, offset=0))

    # Filter todos that have start_time and end_time for proper scheduling
    valid_todos = [
        todo for todo in existing_todos
        if todo.start_time is not None and todo.end_time is not None
    ]

    # Sort by start_time for scheduling logic
    valid_todos.sort(key=lambda x: x.start_time)  # type: ignore
    return valid_todos


def _find_optimal_time_slot(target_date: datetime, parsed_args: ScheduleTodoArgs, existing_todos: list, user_tz: ZoneInfo) -> datetime | None:
    """Find the optimal time slot for scheduling the todo."""
    time_preferences = {
        "morning": (8, 12),   # 8 AM - 12 PM
        "afternoon": (12, 17),  # 12 PM - 5 PM
        "evening": (17, 21)    # 5 PM - 9 PM
    }

    # Try preferred time of day first
    if parsed_args.preferred_time_of_day and parsed_args.preferred_time_of_day.lower() in time_preferences:
        start_hour, end_hour = time_preferences[parsed_args.preferred_time_of_day.lower(
        )]
        suggested_time = _find_free_slot(
            target_date, start_hour, end_hour, parsed_args.duration_minutes, existing_todos, user_tz)
        if suggested_time:
            return suggested_time

    # Try all time slots in order of preference
    for period in ["morning", "afternoon", "evening"]:
        start_hour, end_hour = time_preferences[period]
        suggested_time = _find_free_slot(
            target_date, start_hour, end_hour, parsed_args.duration_minutes, existing_todos, user_tz)
        if suggested_time:
            return suggested_time

    return None


def _handle_no_available_slot(target_date: datetime, parsed_args: ScheduleTodoArgs, existing_todos: list, user_tz: ZoneInfo) -> str:
    """Handle the case when no time slot is available."""
    conflicts = _detect_scheduling_conflicts(
        target_date, parsed_args.duration_minutes, existing_todos, user_tz)
    if conflicts:
        conflict_info = "\n".join(
            [f"  • {c['time']} - {c['item']} (importance: {c['importance']})" for c in conflicts])
        return f"⚠️ No free time slots found for '{parsed_args.item}' on {target_date.strftime('%Y-%m-%d')}.\n\nExisting todos that might conflict:\n{conflict_info}\n\nWould you like me to suggest rescheduling some todos to make room?"
    else:
        return f"⚠️ No suitable time slots found for '{parsed_args.item}' on {target_date.strftime('%Y-%m-%d')}. The day appears to be fully booked."


async def _create_scheduled_todo(parsed_args: ScheduleTodoArgs, suggested_time: datetime) -> Todo:
    """Create a new todo with the suggested time."""
    importance_enum = Importance.NONE
    try:
        importance_enum = Importance(parsed_args.importance.lower())
    except ValueError:
        pass

    # Calculate end time based on duration
    duration_delta = timedelta(minutes=parsed_args.duration_minutes)
    end_time = suggested_time + duration_delta

    # Double-check for time conflicts before creating
    if not _todo_service or not _current_user_id:
        msg = "Todo service not initialized"
        raise RuntimeError(msg)

    conflicts = await _todo_service.check_time_conflict(
        _current_user_id, suggested_time.astimezone(
            UTC), end_time.astimezone(UTC)
    )
    if conflicts:
        conflict_details = [f"'{conflict.item}'" for conflict in conflicts]
        msg = f"Time conflict detected with: {', '.join(conflict_details)}"
        raise RuntimeError(msg)

    todo_data = {
        "item": parsed_args.item,
        "description": parsed_args.description,
        "importance": importance_enum,
        "user_id": _current_user_id,
        "start_time": suggested_time.astimezone(UTC),
        "end_time": end_time.astimezone(UTC),
        "alarm_time": suggested_time.astimezone(UTC)
    }
    return await _todo_service.create(todo_data)


def _format_scheduling_success(todo: Todo, suggested_time: datetime, user_tz: ZoneInfo) -> str:
    """Format the success message for scheduling."""
    suggested_time_str = suggested_time.strftime("%Y-%m-%d %H:%M:%S")
    if user_tz != UTC:
        suggested_time_str += f" ({user_tz})"

    return f"✅ Successfully scheduled '{todo.item}' for {suggested_time_str}\n\nThis time slot was chosen based on your existing schedule and preferences."


def _find_free_slot(target_date: datetime, start_hour: int, end_hour: int, duration_minutes: int, existing_todos: list, user_tz: ZoneInfo) -> datetime | None:
    """Find a free time slot within the specified time range."""
    slot_start = target_date.replace(hour=start_hour, minute=0)
    slot_end = target_date.replace(hour=end_hour, minute=0)
    duration_delta = timedelta(minutes=duration_minutes)

    current_time = slot_start
    for todo in existing_todos:
        # Use start_time and end_time for proper conflict detection
        if todo.start_time and todo.end_time:
            todo_start_local = todo.start_time.astimezone(user_tz)
            todo_end_local = todo.end_time.astimezone(user_tz)
        elif todo.alarm_time:
            # Fallback to alarm_time if start/end times are not available
            todo_start_local = todo.alarm_time.astimezone(user_tz)
            todo_end_local = todo_start_local + \
                timedelta(hours=1)  # Assume 1 hour duration
        else:
            continue

        # Check if there's enough space before this todo
        if current_time + duration_delta <= todo_start_local:
            return current_time

        # Move current time to after this todo
        current_time = max(current_time, todo_end_local)

    # Check if there's space after the last todo
    if current_time + duration_delta <= slot_end:
        return current_time

    return None


def _detect_scheduling_conflicts(target_date: datetime, duration_minutes: int, existing_todos: list, user_tz: ZoneInfo) -> list:
    """Detect potential scheduling conflicts."""
    conflicts = []
    for todo in existing_todos:
        todo_time_local = todo.alarm_time.astimezone(user_tz)
        conflicts.append({
            "time": todo_time_local.strftime("%H:%M"),
            "item": todo.item,
            "importance": todo.importance.value
        })
    return conflicts


async def batch_update_schedule_impl(ctx: RunContextWrapper, args: str) -> str:
    """Apply batch schedule updates after user confirmation."""
    if not _todo_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    try:
        parsed_args = BatchUpdateScheduleArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"

    if not parsed_args.confirm:
        return _generate_update_preview(parsed_args)

    user_tz = _get_user_timezone(parsed_args.timezone)
    if isinstance(user_tz, str):  # Error message
        return user_tz

    successful_updates, failed_updates = await _apply_schedule_updates(parsed_args.updates, user_tz)
    return _format_update_results(successful_updates, failed_updates)


def _generate_update_preview(parsed_args: BatchUpdateScheduleArgs) -> str:
    """Generate a preview of proposed schedule changes."""
    preview = "📋 Proposed Schedule Changes:\n\n"
    for i, update in enumerate(parsed_args.updates, 1):
        preview += f"{i}. Todo ID ending in ...{update.todo_id[-8:]}:\n"
        preview += f"   New time: {update.new_time}\n"
        preview += f"   Reason: {update.reason}\n\n"

    preview += "⚠️  To confirm these changes, set 'confirm: true' in your request."
    return preview


def _get_user_timezone(timezone_str: str | None) -> ZoneInfo | str:
    """Get user timezone or return error message."""
    user_tz = ZoneInfo("UTC")
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError:
            return f"Error: Invalid timezone '{timezone_str}'"
    return user_tz


async def _apply_schedule_updates(updates: list, user_tz: ZoneInfo) -> tuple[list[str], list[str]]:
    """Apply the schedule updates and return results."""
    successful_updates = []
    failed_updates = []

    for update in updates:
        try:
            todo_uuid = UUID(update.todo_id)
            if not _todo_service:
                raise RuntimeError("Todo service not initialized")
            if not _current_user_id:
                raise RuntimeError("Current user ID not set")
            todo = await _todo_service.get_todo_by_id(todo_uuid, _current_user_id)

            if not todo:
                failed_updates.append(f"Todo {update.todo_id} not found")
                continue

            # Parse new time
            try:
                new_time_obj = datetime.strptime(
                    update.new_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)
                new_time_utc = new_time_obj.astimezone(UTC)
            except ValueError:
                failed_updates.append(
                    f"Invalid time format for todo {update.todo_id}: {update.new_time}")
                continue

            # Update the todo
            todo.alarm_time = new_time_utc
            await _todo_service.update(todo)

            successful_updates.append(
                f"✅ '{todo.item}' rescheduled to {update.new_time}")

        except Exception as e:
            failed_updates.append(
                f"Error updating todo {update.todo_id}: {e!s}")

    return successful_updates, failed_updates


def _format_update_results(successful_updates: list[str], failed_updates: list[str]) -> str:
    """Format the batch update results."""
    result = "📅 Schedule Update Results:\n\n"

    if successful_updates:
        result += "Successful updates:\n" + \
            "\n".join(successful_updates) + "\n\n"

    if failed_updates:
        result += "Failed updates:\n" + "\n".join(failed_updates)

    return result


# Create the function tool manually with proper schema
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

When searching todos:
- Use text queries to search in todo items and descriptions
- Filter by importance level if specified
- Filter by date ranges using from_date and to_date
- Support timezone parameter for proper date filtering and display (e.g., 'America/New_York', 'Asia/Shanghai')
- If no timezone is specified, UTC is used for filtering and display
- All times are shown in the user's specified timezone (or UTC if not specified)
- Limit results (default 10) to avoid overwhelming output
- Display results with title, description, start time, end time, alarm time (if set), and importance
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


def get_todo_agent() -> Agent:
    """Create and return a configured todo agent."""
    settings = get_settings()

    model = OpenAIChatCompletionsModel(
        model="doubao-1.5-pro-32k-250115",
        openai_client=AsyncOpenAI(
            api_key=settings.ai.VOLCENGINE_API_KEY,
            base_url=settings.ai.VOLCENGINE_BASE_URL,
        )
    )

    return Agent(
        name="TodoAssistant",
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=[create_todo_tool, delete_todo_tool, update_todo_tool, get_todo_list_tool,
               analyze_schedule_tool, schedule_todo_tool, batch_update_schedule_tool]
    )


def create_todo_agent_session(
    session_id: str,
    user_id: str,
    db_session: "AsyncSession",
    todo_service: TodoService,
    tag_service: TagService,
    session_name: str | None = None,
) -> DatabaseSession:
    """Create a DatabaseSession for persistent todo agent conversations.

    This function creates a database-backed session that integrates with the
    OpenAI Agents SDK, providing persistent conversation history for todo management.

    Args:
        session_id: Unique identifier for the conversation session
        user_id: ID of the user who owns this session
        db_session: SQLAlchemy async session for database operations
        todo_service: TodoService instance for todo operations
        tag_service: TagService instance for tag operations
        session_name: Optional human-readable session name

    Returns:
        DatabaseSession configured for todo agent conversations

    Example:
        >>> # Create session for todo management
        >>> session = create_todo_agent_session(
        ...     session_id=f"user_{user_id}_todo_assistant",
        ...     user_id=user_id,
        ...     db_session=db_session,
        ...     todo_service=todo_service,
        ...     tag_service=tag_service,
        ...     session_name="Todo Management Chat",
        ... )
        >>> 
        >>> # Set agent context for this user
        >>> set_agent_context(todo_service, tag_service, UUID(user_id))
        >>> 
        >>> # Use with OpenAI Agents SDK
        >>> from agents import Runner
        >>> agent = get_todo_agent()
        >>> result = await Runner.run(
        ...     agent,
        ...     "Create a todo item for grocery shopping tomorrow",
        ...     session=session
        ... )
    """
    return DatabaseSession(
        session_id=session_id,
        user_id=user_id,
        db_session=db_session,
        agent_name="TodoAssistant",
        agent_instructions=TODO_SYSTEM_INSTRUCTIONS,
        session_name=session_name or "Todo Management Chat",
    )


class TodoAgentService:
    """Service class for managing todo agent interactions with session persistence.

    This class integrates with the existing agent_sessions domain to provide
    persistent conversation history for todo management agents.
    """

    def __init__(
        self,
        db_session: "AsyncSession",
        todo_service: TodoService,
        tag_service: TagService,
        agent_session_service: AgentSessionService,
        message_service: SessionMessageService,
    ) -> None:
        """Initialize the service with required dependencies.

        Args:
            db_session: SQLAlchemy async session for database operations
            todo_service: TodoService instance for todo operations
            tag_service: TagService instance for tag operations
            agent_session_service: AgentSessionService for session management
            message_service: SessionMessageService for message management
        """
        self.db_session = db_session
        self.todo_service = todo_service
        self.tag_service = tag_service
        self.agent_session_service = agent_session_service
        self.message_service = message_service

    async def chat_with_agent(
        self,
        session_id: str,
        user_id: str,
        message: str,
        session_name: str | None = None,
    ) -> str:
        """Send a message to the todo agent and get a response with persistent conversation history.

        This method integrates with the agent_sessions domain to store conversation history
        and provide context-aware responses.

        Args:
            session_id: Unique identifier for the conversation session
            user_id: ID of the user who owns this session
            message: User message to send to the agent
            session_name: Optional human-readable session name

        Returns:
            Agent's response as a string

        Example:
            >>> service = TodoAgentService(db_session, todo_service, tag_service, agent_session_service, message_service)
            >>> response = await service.chat_with_agent(
            ...     session_id="user_123_todo",
            ...     user_id="user_123",
            ...     message="Create a todo for buying groceries tomorrow at 2 PM",
            ... )
            >>> print(response)
            "I've created a todo item for grocery shopping..."
        """
        # Set the agent context for this user
        set_agent_context(self.todo_service, self.tag_service, UUID(user_id))

        # Create or get existing session using agent sessions service
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))

        if not session:
            # Create new session
            session_data = {
                "session_id": session_id,
                "session_name": session_name or "Todo Management Chat",
                "user_id": UUID(user_id),
                "agent_name": "TodoAssistant",
                "agent_instructions": TODO_SYSTEM_INSTRUCTIONS,
                "is_active": True,
            }
            session = await self.agent_session_service.create(session_data)

        # Store user message in the session
        from app.db.models.session_message import MessageRole
        user_message_data = {
            "session_id": session.id,
            "role": MessageRole.USER,
            "content": message,
            "tool_call_id": None,
            "tool_name": None,
            "extra_data": None,
        }
        await self.message_service.create(user_message_data)

        # Get the todo agent
        agent = get_todo_agent()

        # Run the agent to get response
        result = await Runner.run(agent, message)
        response_content = result.final_output

        # Store assistant response in the session
        assistant_message_data = {
            "session_id": session.id,
            "role": MessageRole.ASSISTANT,
            "content": response_content,
            "tool_call_id": None,
            "tool_name": None,
            "extra_data": None,
        }
        await self.message_service.create(assistant_message_data)

        return response_content

    async def get_session_history(
        self,
        session_id: str,
        user_id: str,
        limit: int | None = None,
    ) -> list[dict]:
        """Get conversation history for a session.

        Args:
            session_id: Unique identifier for the conversation session
            user_id: ID of the user who owns this session
            limit: Optional limit on number of messages to return

        Returns:
            List of message dictionaries in OpenAI format
        """
        # Get session using agent sessions service
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))
        if not session:
            return []

        # Get messages from the session
        messages = await self.message_service.get_recent_messages(session.id, limit or 50)

        # Convert to OpenAI format
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]

    async def clear_session_history(
        self,
        session_id: str,
        user_id: str,
    ) -> None:
        """Clear all messages from a session.

        Args:
            session_id: Unique identifier for the conversation session
            user_id: ID of the user who owns this session
        """
        # Get session using agent sessions service
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))
        if session:
            await self.message_service.clear_session_messages(session.id)

    async def conversation(
        self,
        messages: list[dict],
        session_id: str | None = None,
        user_id: str | None = None,
        session_name: str | None = None,
        agent_name: str | None = None,
        agent_instructions: str | None = None,
    ) -> dict:
        """Handle a conversation with the todo agent following the agent sessions pattern.

        This method follows the same pattern as the agent_sessions conversation endpoint
        to provide consistent API behavior.

        Args:
            messages: List of messages in OpenAI format
            session_id: Optional session identifier
            user_id: User identifier
            session_name: Optional session name
            agent_name: Optional agent name (defaults to "TodoAssistant")
            agent_instructions: Optional agent instructions (defaults to TODO_SYSTEM_INSTRUCTIONS)

        Returns:
            Dictionary with session information and agent response
        """
        if not user_id:
            msg = "user_id is required"
            raise ValueError(msg)

        # Generate session_id if not provided
        if not session_id:
            from datetime import UTC, datetime
            session_id = f"todo_session_{user_id}_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}"

        # Get the last user message for the agent
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message:
            user_message = "Hello"

        # Process the conversation
        response = await self.chat_with_agent(
            session_id=session_id,
            user_id=user_id,
            message=user_message,
            session_name=session_name,
        )

        # Get the session for metadata
        session = await self.agent_session_service.get_by_session_id(session_id, UUID(user_id))
        message_count = await self.message_service.get_session_message_count(session.id) if session else 0

        return {
            "session_id": session_id,
            "session_uuid": str(session.id) if session else None,
            "response": response,
            "messages_count": message_count,
            "session_active": session.is_active if session else True,
        }


# Alias for backward compatibility
TodoAgentSessionService = TodoAgentService


def create_todo_agent_service(
    db_session: "AsyncSession",
    todo_service: TodoService,
    tag_service: TagService,
    agent_session_service: AgentSessionService,
    message_service: SessionMessageService,
) -> TodoAgentService:
    """Factory function to create TodoAgentService with proper dependencies.

    Args:
        db_session: SQLAlchemy async session for database operations
        todo_service: TodoService instance for todo operations
        tag_service: TagService instance for tag operations
        agent_session_service: AgentSessionService for session management
        message_service: SessionMessageService for message management

    Returns:
        Configured TodoAgentService instance
    """
    return TodoAgentService(
        db_session=db_session,
        todo_service=todo_service,
        tag_service=tag_service,
        agent_session_service=agent_session_service,
        message_service=message_service,
    )


async def provide_todo_agent_service(
    db_session: "AsyncSession",
    todo_service: TodoService,
    tag_service: TagService,
    agent_session_service: AgentSessionService,
    message_service: SessionMessageService,
) -> TodoAgentService:
    """Dependency provider for TodoAgentService.

    This function can be used with Litestar's dependency injection system
    to provide TodoAgentService instances to controllers.

    Returns:
        Configured TodoAgentService instance
    """
    return create_todo_agent_service(
        db_session=db_session,
        todo_service=todo_service,
        tag_service=tag_service,
        agent_session_service=agent_session_service,
        message_service=message_service,
    )


# Legacy function maintained for backward compatibility
def get_todo_agent_legacy() -> Agent:
    """Create and return a configured todo agent (legacy function).

    This is the original get_todo_agent function, kept for backward compatibility.
    For new implementations with session support, use TodoAgentService instead.
    """
    return get_todo_agent()
    """Create and return a configured todo agent."""
    settings = get_settings()

    model = OpenAIChatCompletionsModel(
        model="doubao-1.5-pro-32k-250115",
        openai_client=AsyncOpenAI(
            api_key=settings.ai.VOLCENGINE_API_KEY,
            base_url=settings.ai.VOLCENGINE_BASE_URL,
        )
    )

    return Agent(
        name="TodoAssistant",
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=[create_todo_tool, delete_todo_tool, update_todo_tool, get_todo_list_tool,
               analyze_schedule_tool, schedule_todo_tool, batch_update_schedule_tool]
    )
