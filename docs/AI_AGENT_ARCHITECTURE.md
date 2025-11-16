# AI Agent Architecture (OpenAI Agents)

This document provides a comprehensive overview of the AI Agent architecture implemented in the Todo application using the OpenAI Agents framework. The system enables natural language interaction for intelligent todo management with advanced scheduling capabilities, conflict detection, and persistent conversation sessions.

## Table of Contents

1. [OpenAI Agents Framework Integration](#openai-agents-framework-integration)
2. [Agent Factory and Configuration Patterns](#agent-factory-and-configuration-patterns)
3. [Agent Lifecycle Management](#agent-lifecycle-management)
4. [Agent Session Handling and State Management](#agent-session-handling-and-state-management)
5. [Tool Registration and Execution System](#tool-registration-and-execution-system)
6. [Agent Memory and Context Management](#agent-memory-and-context-management)
7. [Multi-Agent Coordination Patterns](#multi-agent-coordination-patterns)
8. [Agent Error Handling and Recovery](#agent-error-handling-and-recovery)
9. [Agent Performance Monitoring and Optimization](#agent-performance-monitoring-and-optimization)
10. [Security Considerations for AI Agents](#security-considerations-for-ai-agents)

## OpenAI Agents Framework Integration

### Framework Overview

The application uses the official OpenAI Agents SDK (`agents` package) to provide sophisticated AI-powered todo management capabilities. The framework offers:

- **Function Tool Integration**: Seamless integration with custom Python functions
- **SQLite Session Persistence**: Built-in conversation history management
- **Streaming Support**: Real-time response streaming for enhanced UX
- **Context Management**: Automatic context preservation across interactions
- **Multi-turn Conversations**: Support for complex, multi-step dialogues

### Model Integration

The system integrates with multiple language model providers through the LiteLLM extension:

```python
from agents.extensions.models.litellm_model import LitellmModel

model = LitellmModel(
    model="openai/glm-4.5",
    api_key=settings.ai.GLM_API_KEY,
    base_url=settings.ai.GLM_BASE_URL,
)
```

### Configuration Structure

The AI configuration is centralized in the application settings:

```python
# src/app/config/base.py
GLM_API_KEY: str | None = field(default_factory=get_env("GLM_API_KEY", None))
"""GLM API Key for GLM models"""

GLM_BASE_URL: str | None = field(default_factory=get_env("GLM_BASE_URL", None))
"""GLM Base URL for API endpoints"""

VOLCENGINE_API_KEY: str | None = field(default_factory=get_env("VOLCENGINE_API_KEY", None))
"""VolcEngine API Key for Doubao models"""

VOLCENGINE_BASE_URL: str | None = field(default_factory=get_env("VOLCENGINE_BASE_URL", None))
"""VolcEngine Base URL for API endpoints"""
```

## Agent Factory and Configuration Patterns

### Factory Pattern Implementation

The agent factory follows a centralized creation pattern to ensure consistency:

```python
# src/app/domain/todo_agents/tools/agent_factory.py
def get_todo_agent() -> Agent:
    """Create and return a configured todo agent with LiteLLM."""
    from agents import Agent
    from agents.extensions.models.litellm_model import LitellmModel

    settings = get_settings()

    model = LitellmModel(
        model="openai/glm-4.5",
        api_key=settings.ai.GLM_API_KEY,
        base_url=settings.ai.GLM_BASE_URL,
    )

    tools = cast("list[Tool]", list(get_tool_definitions()))

    return Agent(
        name="TodoAssistant",
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=tools,
    )
```

### System Instructions Architecture

The system uses comprehensive, role-based instructions that define the agent's capabilities and behavior:

```python
# src/app/domain/todo_agents/tools/system_instructions.py
TODO_SYSTEM_INSTRUCTIONS = f"""You are a personal todo assistant specializing in intelligent schedule management with automatic conflict prevention...

Core Capabilities:
1. Get current date/time information with timezone awareness
2. Get user agent usage quota information
3. Create, read, update, and delete todo items
4. Intelligent schedule analysis with conflict detection
5. Automatic scheduling that prevents time conflicts
6. Batch schedule updates and reorganization
7. Timezone-aware operations for global users
8. Duration-based scheduling with proper time slot allocation
"""
```

### Tool Definition Pattern

Tools are defined using a consistent pattern with Pydantic schemas for validation:

```python
# src/app/domain/todo_agents/tools/tool_definitions.py
def get_tool_definitions() -> Sequence[FunctionTool]:
    """Return the list of FunctionTool definitions for the todo agent."""
    from agents import FunctionTool

    create_todo_tool = FunctionTool(
        name="create_todo",
        description="Create a new todo item using the TodoService.",
        params_json_schema=CreateTodoArgs.model_json_schema(),
        on_invoke_tool=create_todo_impl,
    )

    # Additional tools...

    return [get_user_datetime_tool, get_user_quota_tool, create_todo_tool, ...]
```

## Agent Lifecycle Management

### Service-Based Architecture

The agent lifecycle is managed through a dedicated service class:

```python
# src/app/domain/todo_agents/services.py
class TodoAgentService:
    """Service class for managing todo agent interactions with SQLite session persistence."""

    def __init__(
        self,
        todo_service: "TodoService",
        tag_service: "TagService",
        rate_limit_service: "RateLimitService",
        quota_service: "UserUsageQuotaService",
        session_db_path: str = "conversations.db",
    ) -> None:
        # Dependency injection and initialization
```

### Agent Initialization Process

1. **Context Setup**: Services and user context are injected into the tool context
2. **Session Management**: SQLite sessions are created/retrieved for persistence
3. **Tool Registration**: All available tools are registered with the agent
4. **Rate Limiting**: Usage quotas are checked and enforced
5. **Model Configuration**: Language model is configured and initialized

### Execution Flow

```python
async def chat_with_agent(
    self,
    user_id: str,
    message: str,
    session_id: str | None = None,
) -> str:
    """Send a message to the todo agent and get a response with persistent conversation history."""

    # 1. Rate limiting check
    await self.rate_limit_service.check_and_increment_usage(UUID(user_id), self.quota_service)

    # 2. Session management
    if session_id not in self._sessions:
        self._sessions[session_id] = SQLiteSession(session_id, self.session_db_path)

    # 3. Context setup
    set_agent_context(self.todo_service, self.tag_service, UUID(user_id), ...)

    # 4. Agent execution
    result = await Runner.run(agent, message, session=session, max_turns=20)

    return result.final_output
```

## Agent Session Handling and State Management

### SQLite Session Persistence

The system uses the OpenAI Agents SDK's built-in SQLite session persistence:

```python
# Session creation and management
if session_id not in self._sessions:
    self._sessions[session_id] = SQLiteSession(session_id, self.session_db_path)

session = self._sessions[session_id]
```

### Session ID Pattern

Session IDs follow a structured pattern for user isolation:

```python
session_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
```

### Session Management Endpoints

The API provides comprehensive session management:

- **List Sessions**: `GET /agent-sessions` - List active sessions for the user
- **Create Session**: `POST /agent-sessions/new` - Create a new session
- **Get History**: `GET /agent-sessions/{session_id}/history` - Retrieve conversation history
- **Clear History**: `DELETE /agent-sessions/{session_id}` - Clear session history

### Database Model for Sessions

```python
# src/app/db/models/agent_session.py
class AgentSession(UUIDAuditBase):
    """Agent conversation sessions for OpenAI Agents SDK integration."""

    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id"), nullable=False)

    # Relationships
    user: Mapped[User] = relationship(back_populates="agent_sessions")
    messages: Mapped[list[SessionMessage]] = relationship(back_populates="session")
```

## Tool Registration and Execution System

### Tool Architecture Overview

The tool system follows a modular architecture with clear separation of concerns:

1. **Argument Models**: Pydantic schemas for input validation
2. **Tool Definitions**: FunctionTool configurations
3. **Tool Implementations**: Actual execution logic
4. **Context Management**: Service and user context injection

### Tool Categories

#### Universal Tools
- `get_user_datetime`: Provides current time context for all operations
- `get_user_quota`: Returns usage quota and statistics

#### CRUD Operations
- `create_todo`: Create new todo items with conflict detection
- `update_todo`: Modify existing todos
- `delete_todo`: Remove todos
- `get_todo_list`: Retrieve and filter todos

#### Scheduling Tools
- `schedule_todo`: Intelligent scheduling with conflict avoidance
- `analyze_schedule`: Schedule analysis and free time detection
- `batch_update_schedule`: Batch schedule modifications

### Tool Registration Pattern

```python
# src/app/domain/todo_agents/tools/tool_definitions.py
create_todo_tool = FunctionTool(
    name="create_todo",
    description="Create a new todo item using the TodoService.",
    params_json_schema=CreateTodoArgs.model_json_schema(),
    on_invoke_tool=create_todo_impl,
)
```

### Argument Validation with Pydantic

```python
# src/app/domain/todo_agents/tools/argument_models.py
class CreateTodoArgs(BaseModel):
    item: str = Field(..., description="The name/title of the todo item to create")
    description: str | None = Field(None, description="The description/content of the todo item")
    start_time: str = Field(..., description="The start time for the todo in format YYYY-MM-DD HH:MM:SS")
    end_time: str = Field(..., description="The end time for the todo in format YYYY-MM-DD HH:MM:SS")
    importance: str = Field(default="none", description="The importance level: none, low, medium, high")
    timezone: str | None = Field(None, description="Timezone for date parsing")
```

### Tool Implementation Pattern

```python
# src/app/domain/todo_agents/tools/tool_implementations.py
async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the create_todo function."""
    todo_service = get_todo_service()
    current_user_id = get_current_user_id()

    # Input preprocessing and validation
    args = _preprocess_args(args)
    parsed = CreateTodoArgs.model_validate_json(args)

    # Business logic execution
    # ... conflict detection, todo creation, etc.

    return f"Successfully created todo '{todo.item}' (ID: {todo.id})"
```

## Agent Memory and Context Management

### Global Context Pattern

The system uses a thread-local context pattern for service injection:

```python
# src/app/domain/todo_agents/tools/tool_context.py
# Global context variables (set per user/session)
_todo_service: TodoService | None = None
_tag_service: TagService | None = None
_current_user_id: UUID | None = None

def set_agent_context(
    todo_service: TodoService,
    tag_service: TagService,
    user_id: UUID,
    quota_service: UserUsageQuotaService | None = None,
) -> None:
    """Inject services & user context for subsequent tool calls."""
    global _todo_service, _tag_service, _current_user_id, _quota_service
    _todo_service = todo_service
    _tag_service = tag_service
    _current_user_id = user_id
    _quota_service = quota_service
```

### Context Lifecycle Management

1. **Context Setting**: Before each agent interaction, user-specific context is set
2. **Tool Access**: Tools access context through getter functions
3. **Context Cleanup**: Context is cleared after each interaction
4. **Isolation**: Each user gets isolated context to prevent cross-contamination

### Memory Persistence Strategies

- **SQLite Sessions**: Conversation history is automatically persisted
- **Context Injection**: Services are injected per-request
- **User Isolation**: Session IDs ensure user data isolation
- **Session State**: Active sessions are tracked in memory

## Multi-Agent Coordination Patterns

### Current Implementation

The current system uses a single-agent architecture with the TodoAssistant. However, the architecture supports multi-agent expansion:

### Agent Role Specialization

```python
# Potential multi-agent architecture
SCHEDULING_AGENT = Agent(
    name="ScheduleAssistant",
    instructions="Specialized in scheduling and time management...",
    model=model,
    tools=scheduling_tools,
)

CRUD_AGENT = Agent(
    name="TodoCRUDAssistant",
    instructions="Specialized in todo CRUD operations...",
    model=model,
    tools=crud_tools,
)
```

### Coordination Patterns

#### Sequential Coordination
```python
# Agent handoff pattern
async def handle_complex_request(message: str, user_id: str):
    # First, determine the required operations
    analysis = await analysis_agent.analyze_request(message, user_id)

    # Then, execute with specialized agents
    if analysis.requires_scheduling:
        result = await scheduling_agent.schedule(analysis.scheduling_data, user_id)

    if analysis.requires_crud:
        result = await crud_agent.execute_crud(analysis.crud_data, user_id)
```

#### Hierarchical Coordination
```python
# Master coordinator agent
COORDINATOR_AGENT = Agent(
    name="TodoCoordinator",
    instructions="Coordinate between specialized agents...",
    tools=coordination_tools,
)
```

## Agent Error Handling and Recovery

### Error Handling Strategy

The system implements comprehensive error handling at multiple levels:

#### 1. Tool-Level Error Handling
```python
async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    try:
        # Tool execution logic
        parsed = CreateTodoArgs.model_validate_json(args)
        # ... business logic
    except ValueError as e:
        return f"Error: Invalid arguments '{args}': {e}"
    except Exception as e:
        return f"Error creating todo: {e!s}"
```

#### 2. Service-Level Error Handling
```python
async def chat_with_agent(self, user_id: str, message: str, session_id: str | None = None) -> str:
    try:
        # Agent execution
        result = await Runner.run(agent, message, session=session, max_turns=20)
        return result.final_output
    except RateLimitExceededException as e:
        return f"You have exceeded your monthly usage limit. {e.detail}"
    except Exception as e:
        logger.exception("Agent execution failed", error=str(e))
        return f"An error occurred while processing your request: {e!s}"
```

#### 3. Controller-Level Error Handling
```python
@post(path="/agent-create")
async def agent_create_todo(self, current_user: m.User, data: AgentTodoRequest, ...):
    try:
        # Controller logic
        response = await todo_agent_service.chat_with_agent(...)
        return AgentTodoResponse(status="success", ...)
    except RateLimitExceededException as e:
        return RateLimitErrorResponse(
            message=e.detail,
            current_usage=e.current_usage,
            monthly_limit=e.monthly_limit,
            ...
        )
```

### Error Recovery Patterns

#### Retry Mechanism
```python
# Configurable retry for transient failures
@retry(max_attempts=3, backoff=exponential)
async def execute_tool_with_retry(tool_func, *args, **kwargs):
    return await tool_func(*args, **kwargs)
```

#### Graceful Degradation
```python
# Fallback when advanced features fail
try:
    result = await schedule_todo_intelligently(todo_data)
except SchedulingError:
    # Fall back to basic scheduling
    result = await schedule_todo_basic(todo_data)
```

#### Error Context Preservation
```python
# Maintain context during errors
error_context = {
    "user_id": current_user_id,
    "session_id": session_id,
    "message": message,
    "error": str(e),
    "timestamp": datetime.now(UTC)
}
logger.error("Agent operation failed", extra=error_context)
```

## Agent Performance Monitoring and Optimization

### Performance Monitoring

#### 1. Usage Tracking
```python
# src/app/lib/rate_limit_service.py
async def check_and_increment_usage(self, user_id: UUID, quota_service) -> None:
    usage_count = await self.get_current_usage(user_id)
    monthly_limit = await quota_service.get_monthly_limit(user_id)

    if usage_count >= monthly_limit:
        raise RateLimitExceededException(...)
```

#### 2. Response Time Monitoring
```python
# Timing agent interactions
async def chat_with_agent_with_timing(user_id: str, message: str, session_id: str) -> str:
    start_time = time.time()

    try:
        result = await self.chat_with_agent(user_id, message, session_id)
        response_time = time.time() - start_time

        # Log performance metrics
        logger.info("Agent interaction completed",
                   user_id=user_id,
                   response_time=response_time,
                   message_length=len(message))

        return result
    except Exception as e:
        logger.error("Agent interaction failed",
                    user_id=user_id,
                    response_time=time.time() - start_time,
                    error=str(e))
        raise
```

#### 3. Session Health Monitoring
```python
def list_active_sessions(self) -> list[str]:
    """List all active session IDs currently in memory."""
    active_sessions = list(self._sessions.keys())

    # Log session statistics
    logger.info("Active sessions monitoring",
               total_sessions=len(active_sessions),
               session_ids=active_sessions)

    return active_sessions
```

### Optimization Strategies

#### 1. Session Pooling
```python
# Session reuse and cleanup
class SessionPool:
    def __init__(self, max_sessions: int = 100):
        self.max_sessions = max_sessions
        self.session_access_time = {}

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove inactive sessions to free memory."""
        cutoff_time = time.time() - (max_age_hours * 3600)

        old_sessions = [
            session_id for session_id, last_access in self.session_access_time.items()
            if last_access < cutoff_time
        ]

        for session_id in old_sessions:
            self.remove_session(session_id)
```

#### 2. Caching Strategy
```python
# Cache frequently accessed data
@lru_cache(maxsize=100)
def get_cached_user_timezone(user_id: str) -> str:
    """Cache user timezone preferences."""
    return get_user_timezone_from_db(user_id)
```

#### 3. Streaming Optimization
```python
# Efficient streaming for large responses
async def stream_chat_with_agent(self, user_id: str, message: str, session_id: str):
    """Stream agent responses to improve perceived performance."""

    # Early session initialization
    yield {"event": "session_initialized", "data": {"session_id": session_id}}

    # Stream response chunks
    async for event in stream.stream_events():
        # Process and emit events immediately
        processed_event = self._process_stream_event(event)
        yield processed_event
```

#### 4. Database Query Optimization
```python
# Efficient todo retrieval with proper indexing
async def get_todo_list_impl(ctx: RunContextWrapper, args: str) -> str:
    """Optimized todo retrieval with pagination and filtering."""

    # Use proper filters and limits
    filters = [m.Todo.user_id == current_user_id]

    # Apply date filters efficiently
    if parsed.from_date:
        filters.append(m.Todo.alarm_time >= from_date_obj.astimezone(UTC))

    # Use pagination for large datasets
    from advanced_alchemy.filters import LimitOffset
    todos, total = await todo_service.list_and_count(
        *filters,
        LimitOffset(limit=parsed.limit, offset=0)
    )
```

### Performance Metrics

Key performance indicators monitored:

1. **Response Time**: Average time per agent interaction
2. **Throughput**: Requests processed per minute
3. **Error Rate**: Percentage of failed interactions
4. **Session Health**: Active vs inactive session ratios
5. **Resource Usage**: Memory and CPU consumption
6. **Database Performance**: Query execution times

## Security Considerations for AI Agents

### Data Security and Privacy

#### 1. User Data Isolation
```python
# Strict user isolation in all operations
async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    current_user_id = get_current_user_id()

    # All operations are scoped to the current user
    todo_data["user_id"] = current_user_id

    # Verification that todo belongs to user
    if todo.user_id != current_user_id:
        return "Access denied: This todo does not belong to you"
```

#### 2. Input Validation and Sanitization
```python
# Comprehensive input validation
def _preprocess_args(args: str) -> str:
    """Preprocess tool arguments to handle double-encoded JSON arrays."""
    try:
        data = json.loads(args)

        # Validate and sanitize all inputs
        for key, value in data.items():
            if isinstance(value, str):
                # Sanitize string inputs
                data[key] = sanitize_input(value)

        return json.dumps(data)
    except json.JSONDecodeError:
        # Reject malformed input
        raise ValueError("Invalid input format")
```

#### 3. Rate Limiting and Quota Management
```python
# Enforce usage limits
async def check_and_increment_usage(self, user_id: UUID, quota_service) -> None:
    usage_count = await self.get_current_usage(user_id)
    monthly_limit = await quota_service.get_monthly_limit(user_id)

    if usage_count >= monthly_limit:
        raise RateLimitExceededException(
            detail="Monthly usage limit exceeded",
            current_usage=usage_count,
            monthly_limit=monthly_limit
        )
```

#### 4. Sensitive Information Protection
```python
# PII column identification
class AgentSession(UUIDAuditBase):
    __pii_columns__ = {"session_name", "session_id"}

    # Sensitive data is marked as PII
    session_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

### Access Control

#### 1. Authentication Integration
```python
# All agent endpoints require authentication
@post(path="/agent-create")
async def agent_create_todo(
    self,
    current_user: m.User,  # Authenticated user from JWT
    data: AgentTodoRequest,
    todo_agent_service: TodoAgentService,
) -> AgentTodoResponse:
    # Agent operations are only available to authenticated users
```

#### 2. Authorization Checks
```python
# Verify user permissions on all operations
async def delete_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    todo = await todo_service.get(todo_uuid)

    # Authorization check
    if todo.user_id != current_user_id:
        return f"Todo item with ID {parsed.todo_id} does not belong to you."

    await todo_service.delete(todo_uuid)
```

#### 3. Session Security
```python
# Secure session ID generation
session_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"

# Session isolation enforced
user_sessions = [
    session_id for session_id in sessions
    if session_id.startswith(f"user_{current_user.id}_")
]
```

### API Security

#### 1. Input Validation
```python
# Strict schema validation for all inputs
class AgentTodoRequest(PydanticBaseModel):
    messages: list[dict[str, Any]] = Field(..., description="List of conversation messages")
    session_id: str | None = Field(None, description="Optional session ID for conversation persistence")

    # Validate message structure
    @validator('messages')
    def validate_messages(cls, v):
        for message in v:
            if not isinstance(message, dict):
                raise ValueError("Each message must be a dictionary")
            if 'role' not in message or 'content' not in message:
                raise ValueError("Messages must contain 'role' and 'content'")
        return v
```

#### 2. Output Sanitization
```python
# Sanitize agent outputs to prevent information leakage
def sanitize_agent_output(output: str) -> str:
    """Remove sensitive information from agent responses."""
    # Remove internal IDs
    output = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[ID]', output)

    # Remove system paths
    output = re.sub(r'/[a-zA-Z0-9/_-]+', '[PATH]', output)

    return output
```

#### 3. SQL Injection Prevention
```python
# Use parameterized queries through SQLAlchemy
todos, total = await todo_service.list_and_count(
    m.Todo.user_id == current_user_id,  # Safe parameterized filter
    LimitOffset(limit=parsed.limit, offset=0)
)
```

### Security Best Practices

1. **Principle of Least Privilege**: Tools only access data they absolutely need
2. **Defense in Depth**: Multiple layers of security validation
3. **Audit Logging**: All agent interactions are logged for security review
4. **Regular Security Reviews**: Periodic assessment of agent tool security
5. **Input Sanitization**: All user inputs are validated and sanitized
6. **Output Filtering**: Sensitive information is filtered from agent responses

## Conclusion

The AI Agent architecture in this Todo application demonstrates a sophisticated implementation of the OpenAI Agents framework with enterprise-grade considerations:

- **Modular Design**: Clean separation between agent factory, tools, and services
- **Robust Session Management**: Persistent conversations with SQLite integration
- **Comprehensive Tool System**: Well-structured CRUD and scheduling capabilities
- **Error Resilience**: Multi-level error handling and recovery mechanisms
- **Performance Optimization**: Efficient resource management and monitoring
- **Security-First Approach**: Comprehensive security measures at all levels

The architecture is designed for scalability, maintainability, and security while providing an intelligent, user-friendly todo management experience. The modular design allows for easy extension with additional agents, tools, and capabilities as the application evolves.

Key architectural strengths:
- **Clean Separation of Concerns**: Each component has a well-defined responsibility
- **Robust Error Handling**: Graceful degradation and recovery mechanisms
- **Security Integration**: Comprehensive security measures throughout the stack
- **Performance Awareness**: Optimized for efficient resource usage
- **Extensibility**: Designed to accommodate future enhancements and new capabilities

This architecture serves as a solid foundation for building sophisticated AI-powered applications that require natural language interfaces, intelligent automation, and enterprise-grade reliability.