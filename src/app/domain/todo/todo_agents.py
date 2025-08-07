from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from agents import Agent, FunctionTool, OpenAIChatCompletionsModel, RunContextWrapper
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config.base import get_settings
from app.db import models as m
from app.db.models.importance import Importance
from app.domain.todo.services import TagService, TodoService


class CreateTodoArgs(BaseModel):
    item: str = Field(...,
                      description="The name/title of the todo item to create")
    description: str | None = Field(
        default=None, description="The description/content of the todo item")
    plan_time: str | None = Field(
        default=None, description="The planned date/time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified")
    tags: list[str] | None = Field(
        default=None, description="List of tag names to associate with the todo. Common tags: 'work', 'personal', 'study', 'entertainment'")
    importance: str = Field(
        default="none", description="The importance level: none, low, medium, high")


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
    plan_time: str | None = Field(
        default=None, description="The new planned date/time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified")
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

    # Parse plan_time if provided and convert to ISO string
    plan_time_obj = None
    if parsed_args.plan_time:
        try:
            plan_time_obj = datetime.strptime(
                parsed_args.plan_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            try:
                plan_time_obj = datetime.strptime(
                    parsed_args.plan_time, "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError:
                return f"Error: Invalid date format '{parsed_args.plan_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

    # Convert importance string to enum
    try:
        importance_enum = Importance(parsed_args.importance.lower())
    except ValueError:
        importance_enum = Importance.NONE

    # Create todo data - handle None plan_time properly
    todo_data: dict[str, object] = {
        "item": parsed_args.item,
        "description": parsed_args.description,
        "importance": importance_enum,
        "user_id": _current_user_id,
    }

    # Only add plan_time if it was provided
    if plan_time_obj is not None:
        todo_data["plan_time"] = plan_time_obj

    # Create the todo - simplified without tag handling for now
    try:
        print(todo_data)
        todo = await _todo_service.create(todo_data)
    except Exception as e:
        return f"Error creating todo: {e!s}"
    else:
        # Return simple success message
        tag_info = f" (tags: {', '.join(parsed_args.tags)})" if parsed_args.tags else ""
        return f"Successfully created todo '{todo.item}' (ID: {todo.id}){tag_info}"


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

    # Determine timezone to use for plan_time parsing
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

    # Parse plan_time if provided with timezone support
    if parsed_args.plan_time is not None:
        try:
            # First try with full datetime format
            plan_time_obj = datetime.strptime(
                parsed_args.plan_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)
        except ValueError:
            try:
                # Then try with date only format (set to beginning of day)
                plan_time_obj = datetime.strptime(
                    parsed_args.plan_time, "%Y-%m-%d").replace(tzinfo=user_tz)
            except ValueError:
                return f"Error: Invalid date format '{parsed_args.plan_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

        # Convert to UTC for database storage
        plan_time_utc = plan_time_obj.astimezone(UTC)
        update_data["plan_time"] = plan_time_utc

    # Convert importance string to enum if provided
    if parsed_args.importance is not None:
        try:
            importance_enum = Importance(parsed_args.importance.lower())
            update_data["importance"] = importance_enum
        except ValueError:
            return f"Error: Invalid importance level '{parsed_args.importance}'. Use: none, low, medium, high"

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

        if "plan_time" in update_data:
            todo.plan_time = update_data["plan_time"]  # type: ignore
            updated_fields.append("plan_time")

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

    # Date range filters for plan_time
    if parsed_args.from_date:
        try:
            # Parse date in user's timezone and convert to UTC for database query
            from_date_obj = datetime.strptime(
                parsed_args.from_date, "%Y-%m-%d").replace(tzinfo=user_tz)
            from_date_utc = from_date_obj.astimezone(UTC)
            filters.append(m.Todo.plan_time >= from_date_utc)
        except ValueError:
            return f"Error: Invalid from_date format '{parsed_args.from_date}'. Use YYYY-MM-DD"

    if parsed_args.to_date:
        try:
            # Parse date in user's timezone, set to end of day, and convert to UTC
            to_date_obj = datetime.strptime(
                parsed_args.to_date, "%Y-%m-%d").replace(tzinfo=user_tz, hour=23, minute=59, second=59)
            to_date_utc = to_date_obj.astimezone(UTC)
            filters.append(m.Todo.plan_time <= to_date_utc)
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
            if todo.plan_time:
                # Convert UTC time from database to user's timezone for display
                plan_time_in_user_tz = todo.plan_time.astimezone(user_tz)
                plan_time_str = plan_time_in_user_tz.strftime(
                    "%Y-%m-%d %H:%M:%S")
                if user_tz != UTC:
                    # Show timezone info if not UTC
                    plan_time_str += f" ({plan_time_in_user_tz.tzinfo})"
            else:
                plan_time_str = "No plan time"
            result = f"• {todo.item} (ID: {todo.id})\n  Description: {todo.description or 'No description'}\n  Plan time: {plan_time_str}\n  Importance: {todo.importance.value}"
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


TODO_SYSTEM_INSTRUCTIONS = f"""You are a helpful todo list assistant. You can create, delete, update, and search todo items based on user input.

When creating todos:
- Extract the main task as the 'item' (title)
- Use any additional details as 'description'
- Parse dates/times if mentioned for 'plan_time' (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
- Assign appropriate importance: none (default), low, medium, high
- Suggest relevant tags like: 'work', 'personal', 'study', 'shopping', 'health', 'entertainment'
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
- Parse dates/times if mentioned for 'plan_time' (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
- Support timezone parameter for proper date parsing (e.g., 'America/New_York', 'Asia/Shanghai')
- If no timezone is specified, UTC is used for date parsing
- Validate importance levels: none, low, medium, high
- Do not return the ID of the user and todo items.

When listing todos:
- Use the get_todo_list tool to show all todos for the current user
- Support filtering by date range (from_date, to_date) and importance level
- Support timezone parameter for proper date filtering and display (e.g., 'America/New_York', 'Asia/Shanghai')
- If no timezone is specified, UTC is used for filtering and display
- Display results with ID, title, description, plan time, and importance
- Plan times are shown in the user's specified timezone (or UTC if not specified)
- Limit results to avoid overwhelming output (default 20)
- Show applied filters in the response for clarity
- Do not return the ID of the user and todo items.

When searching todos:
- Use text queries to search in todo items and descriptions
- Filter by importance level if specified
- Filter by date ranges using from_date and to_date
- Support timezone parameter for proper date filtering and display (e.g., 'America/New_York', 'Asia/Shanghai')
- If no timezone is specified, UTC is used for filtering and display
- Plan times are shown in the user's specified timezone (or UTC if not specified)
- Limit results (default 10) to avoid overwhelming output
- Display results with, title, description, plan time, and importance
- Do not return the ID of the user and todo items.

If the user's input is unclear, ask for clarification. Always be helpful and ensure a smooth user experience. When you return the results, do not include any sensitive information or personal data, and do not return the UUID of the user and todo items.

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
        tools=[create_todo_tool, delete_todo_tool,
               update_todo_tool, get_todo_list_tool]
    )
