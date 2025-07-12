from datetime import datetime
from uuid import UUID

from agents import Agent, FunctionTool, OpenAIChatCompletionsModel, RunContextWrapper
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config.base import get_settings
from app.db.models.importance import Importance
from app.domain.todo.services import TagService, TodoService


class CreateTodoArgs(BaseModel):
    item: str = Field(..., description="The name/title of the todo item to create")
    description: str | None = Field(default=None, description="The description/content of the todo item")
    plan_time: str | None = Field(default=None, description="The planned date/time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD, can be None if not specified")
    tags: list[str] | None = Field(default=None, description="List of tag names to associate with the todo. Common tags: 'work', 'personal', 'study', 'entertainment'")
    importance: str = Field(default="none", description="The importance level: none, low, medium, high")


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


async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the create_todo function."""
    if not _todo_service or not _tag_service or not _current_user_id:
        return "Error: Agent context not properly initialized"

    try:
        # Parse the arguments
        parsed_args = CreateTodoArgs.model_validate_json(args)

        # Parse plan_time if provided
        plan_time_obj = None
        if parsed_args.plan_time:
            try:
                plan_time_obj = datetime.strptime(parsed_args.plan_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    # Try date only format
                    plan_time_obj = datetime.strptime(parsed_args.plan_time, "%Y-%m-%d")
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
        todo = await _todo_service.create(todo_data)

        # Return simple success message
        tag_info = f" (tags: {', '.join(parsed_args.tags)})" if parsed_args.tags else ""
        return f"Successfully created todo '{todo.item}' (ID: {todo.id}){tag_info}"

    except Exception as e:
        return f"Error creating todo: {e!s}"


# Create the function tool manually with proper schema
create_todo_tool = FunctionTool(
    name="create_todo",
    description="Create a new todo item using the TodoService.",
    params_json_schema=CreateTodoArgs.model_json_schema(),
    on_invoke_tool=create_todo_impl,
)


SYSTEM_INSTRUCTIONS = f"""You are a helpful todo list assistant. You can create todo items based on user input.

When creating todos:
- Extract the main task as the 'item' (title)
- Use any additional details as 'description'
- Parse dates/times if mentioned for 'plan_time' (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
- Assign appropriate importance: none (default), low, medium, high
- Suggest relevant tags like: 'work', 'personal', 'study', 'shopping', 'health', 'entertainment'

If the user's input is unclear, ask for clarification. Always be helpful and create meaningful todos.

Today's date is {datetime.now().strftime('%Y-%m-%d')}."""


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
        instructions=SYSTEM_INSTRUCTIONS,
        model=model,
        tools=[create_todo_tool]
    )
