from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import structlog
from advanced_alchemy.filters import FilterTypes
from advanced_alchemy.service import OffsetPagination
from litestar import Controller, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Dependency
from pydantic import BaseModel

import app.db.models as m
from app.domain.todo.deps import provide_tag_service, provide_todo_service
from app.domain.todo.schemas import AgentTodoResponse, TagCreate, TagModel, TodoCreate, TodoModel
from app.domain.todo.services import TagService, TodoService
from app.domain.todo.todo_agents import TodoAgentSessionService
from app.lib.deps import create_filter_dependencies

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class AgentTodoRequest(BaseModel):
    """Request schema for AI agent todo creation."""
    messages: list[dict[str, Any]]
    session_id: str | None = None  # Optional session ID for conversation persistence
    session_name: str | None = None  # Optional human-readable session name


class TodoController(Controller):
    """Controller for managing todo items."""

    tags = ["Todo"]

    dependencies = {
        "todo_service": Provide(provide_todo_service),
        "tag_service": Provide(provide_tag_service),
    } | create_filter_dependencies(
        {
            "id_filter": UUID,
            "search": "item",
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "created_time",
            "sort_order": "asc",
        },
    )

    path = "/todos"

    @get(path="/", operation_id="list_todos")
    async def list_todos(self, current_user: m.User, todo_service: TodoService, filters: Annotated[list[FilterTypes], Dependency(skip_validation=True)]) -> OffsetPagination[TodoModel]:
        """List all todo items."""
        user_filter = m.Todo.user_id == current_user.id
        results, total = await todo_service.list_and_count(user_filter, *filters)
        return todo_service.to_schema(data=results, total=total, schema_type=TodoModel, filters=filters)

    @post(path="/", operation_id="create_todo")
    async def create_todo(self, current_user: m.User, data: TodoCreate, todo_service: TodoService) -> TodoModel:
        """Create a new todo item."""
        todo_dict = data.to_dict()
        todo_dict["user_id"] = current_user.id
        print(todo_dict)
        todo_model = await todo_service.create(todo_dict)
        return todo_service.to_schema(todo_model, schema_type=TodoModel)

    @get(path="/{todo_id:uuid}", operation_id="get_todo")
    async def get_todo(self, todo_id: UUID, todo_service: TodoService) -> TodoModel | str:
        try:
            """Get a specific todo item by ID."""
            todo = await todo_service.get(todo_id)
            if not todo:
                return f"Todo item {todo_id} not found."
            return todo_service.to_schema(todo, schema_type=TodoModel)
        except Exception as e:
            return f"Error retrieving todo item {todo_id}: {e!s}"

    @patch(path="/{todo_id:uuid}", operation_id="update_todo")
    async def update_todo(self, todo_id: UUID, data: TodoCreate, todo_service: TodoService) -> str | TodoModel:
        """Update a specific todo item by ID."""
        todo = await todo_service.get(todo_id)
        if not todo:
            return f"Todo item {todo_id} not found."
        todo_dict = data.to_dict()
        updated_todo = await todo_service.update(todo, **todo_dict)
        return todo_service.to_schema(updated_todo, schema_type=TodoModel)

    @delete(path="/{todo_id:uuid}", operation_id="delete_todo", status_code=200)
    async def delete_todo(self, todo_id: UUID, todo_service: TodoService) -> str | TodoModel:
        try:
            """Delete a specific todo item by ID."""
            todo = await todo_service.get(todo_id)
            if not todo:
                return f"Todo item {todo_id} not found."
            await todo_service.delete(todo_id)
            return todo_service.to_schema(todo,     schema_type=TodoModel)
        except Exception as e:
            return f"Error deleting todo item {todo_id}: {e!s}"

    @post(path="/create_tag", operation_id="create_tag")
    async def create_tag(self, current_user: m.User, data: TagCreate, tag_service: TagService, todo_service: TodoService) -> TagModel:
        """Create a new tag."""

        tag_model = await tag_service.get_or_create_tag(current_user.id, data.name, data.color)
        current_todo_uuid = data.todo_id
        if current_todo_uuid:
            # If a todo is provided, associate the tag with it
            todo_tag = m.TodoTag(
                todo_id=current_todo_uuid, tag_id=tag_model.id)
            current_todo = await todo_service.get(current_todo_uuid)
            if current_todo:
                current_todo.todo_tags.append(todo_tag)

        return tag_service.to_schema(tag_model, schema_type=TagModel)

    @delete(path="/delete_tag/{tag_id:uuid}", operation_id="delete_tag", status_code=200)
    async def delete_tag(self, tag_id: UUID, current_user: m.User, tag_service: TagService) -> str | TagModel:
        """Delete a specific tag by ID."""
        tag = await tag_service.get_one_or_none(m.Tag.id == tag_id, m.Tag.user_id == current_user.id)
        if not tag:
            return f"Tag {tag_id} not found or does not belong to the user."

        await tag_service.delete(tag)

        return tag_service.to_schema(tag, schema_type=TagModel)

    @get(path="/tags", operation_id="list_tags")
    async def list_tags(self, current_user: m.User, tag_service: TagService, filters: Annotated[list[FilterTypes], Dependency(skip_validation=True)]) -> OffsetPagination[TagModel]:
        """List all tags for the current user."""
        user_filter = m.Tag.user_id == current_user.id
        results, total = await tag_service.list_and_count(user_filter, *filters)
        return tag_service.to_schema(data=results, total=total, schema_type=TagModel, filters=filters)

    @post(path="/agent-create", operation_id="agent_create_todo")
    async def agent_create_todo(
        self,
        current_user: m.User,
        data: AgentTodoRequest,
        todo_service: TodoService,
        tag_service: TagService,
        db_session: "AsyncSession"
    ) -> AgentTodoResponse:
        """Create a todo using AI agent with persistent conversation sessions."""
        try:
            # Create the TodoAgentSessionService with database session
            agent_service = TodoAgentSessionService(
                db_session=db_session,
                todo_service=todo_service,
                tag_service=tag_service
            )

            # Generate session ID if not provided
            session_id = data.session_id or f"user_{current_user.id}_todo_agent"

            # Extract the user message from the messages list
            # Assume the last message is the user's input
            if not data.messages:
                return AgentTodoResponse(
                    status="error",
                    message="No messages provided",
                    agent_response=[]
                )

            # Get the last user message
            user_message = ""
            for msg in reversed(data.messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

            if not user_message:
                return AgentTodoResponse(
                    status="error",
                    message="No user message found in messages",
                    agent_response=[]
                )

            # Use the session-based agent to process the message
            response = await agent_service.chat_with_agent(
                session_id=session_id,
                user_id=str(current_user.id),
                message=user_message,
                session_name=data.session_name or "Todo Management Chat"
            )

            # Get the conversation history to return as agent_response
            conversation_history = await agent_service.get_session_history(
                session_id=session_id,
                user_id=str(current_user.id),
                limit=10  # Return last 10 messages
            )

            return AgentTodoResponse(
                status="success",
                message=response,
                agent_response=conversation_history
            )

        except Exception as e:
            logger.exception("Agent todo creation failed",
                             error=str(e), user_id=current_user.id)
            return AgentTodoResponse(
                status="error",
                message=f"Failed to process todo with AI agent: {e!s}",
                agent_response=[]
            )

    @get(path="/agent-sessions", operation_id="list_agent_sessions")
    async def list_agent_sessions(
        self,
        current_user: m.User,
        todo_service: TodoService,
        tag_service: TagService,
        db_session: "AsyncSession"
    ) -> dict[str, Any]:
        """List all agent sessions for the current user."""
        try:
            agent_service = TodoAgentSessionService(
                db_session=db_session,
                todo_service=todo_service,
                tag_service=tag_service
            )

            sessions = await agent_service.list_user_sessions(str(current_user.id))

            return {
                "status": "success",
                "sessions": sessions
            }

        except Exception as e:
            logger.exception("Failed to list agent sessions",
                             error=str(e), user_id=current_user.id)
            return {
                "status": "error",
                "message": f"Failed to list agent sessions: {e!s}",
                "sessions": []
            }

    @get(path="/agent-sessions/{session_id:str}/history", operation_id="get_session_history")
    async def get_session_history(
        self,
        session_id: str,
        current_user: m.User,
        todo_service: TodoService,
        tag_service: TagService,
        db_session: "AsyncSession",
        limit: int = 50
    ) -> dict[str, Any]:
        """Get conversation history for a specific session."""
        try:
            agent_service = TodoAgentSessionService(
                db_session=db_session,
                todo_service=todo_service,
                tag_service=tag_service
            )

            history = await agent_service.get_session_history(
                session_id=session_id,
                user_id=str(current_user.id),
                limit=limit
            )

            return {
                "status": "success",
                "session_id": session_id,
                "history": history
            }

        except Exception as e:
            logger.exception("Failed to get session history",
                             error=str(e), user_id=current_user.id, session_id=session_id)
            return {
                "status": "error",
                "message": f"Failed to get session history: {e!s}",
                "history": []
            }

    @delete(path="/agent-sessions/{session_id:str}", operation_id="clear_session_history", status_code=200)
    async def clear_session_history(
        self,
        session_id: str,
        current_user: m.User,
        todo_service: TodoService,
        tag_service: TagService,
        db_session: "AsyncSession"
    ) -> dict[str, Any]:
        """Clear conversation history for a specific session."""
        try:
            agent_service = TodoAgentSessionService(
                db_session=db_session,
                todo_service=todo_service,
                tag_service=tag_service
            )

            await agent_service.clear_session_history(
                session_id=session_id,
                user_id=str(current_user.id)
            )

            return {
                "status": "success",
                "message": f"Session {session_id} history cleared successfully"
            }

        except Exception as e:
            logger.exception("Failed to clear session history",
                             error=str(e), user_id=current_user.id, session_id=session_id)
            return {
                "status": "error",
                "message": f"Failed to clear session history: {e!s}"
            }
