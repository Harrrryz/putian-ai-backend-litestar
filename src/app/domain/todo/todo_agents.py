from datetime import datetime, timezone
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
        plan_time = parsed_args.plan_time
        item = parsed_args.item
    except ValueError:
        return f"Error: Invalid todo ID '{args}'"

    # Delete the todo item
    try:
        todo_uuid = UUID(todo_id)
        todo = await _todo_service.get(todo_uuid)
        if not todo:
            return f"Todo item with ID {todo_id} not found."

        # Verify the todo belongs to the current user
        if todo.user_id != _current_user_id:
            return f"Todo item with ID {todo_id} does not belong to you."

        await _todo_service.delete(item)
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
        from datetime import timezone
        try:
            plan_time_obj = datetime.strptime(
                parsed_args.plan_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                plan_time_obj = datetime.strptime(
                    parsed_args.plan_time, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                return f"Error: Invalid date format '{parsed_args.plan_time}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"

    # Convert importance string to enum
    try:
        importance_enum = Importance(parsed_args.importance.lower())
    except ValueError:
        importance_enum = Importance.NONE

    # Create todo data - handle None plan_time properly
    todo_data = {
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

TODO_SYSTEM_INSTRUCTIONS = f"""You are a helpful todo list assistant. You can create, delete, change todo items based on user input.

When creating todos:
- Extract the main task as the 'item' (title)
- Use any additional details as 'description'
- Parse dates/times if mentioned for 'plan_time' (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
- Assign appropriate importance: none (default), low, medium, high
- Suggest relevant tags like: 'work', 'personal', 'study', 'shopping', 'health', 'entertainment'

If the user's input is unclear, ask for clarification. Always be helpful and create meaningful todos.

When deleting todos:
- Get the necessary information about the todo item to delete, such as 'item' (title) and 'plan_time' (if specified). If the user provides a specific date/time, use it to find the todo item.
- If the user does not provide a specific date/time, ask the user to clarify which todo item they want to delete (e.g., by providing the title or other identifying information).


If the user's input is unclear, ask for clarification. Always be helpful and ensure a smooth deletion process.

Today's date is {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}."""


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
        tools=[create_todo_tool, delete_todo_tool]
    )
