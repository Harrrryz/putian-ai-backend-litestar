# Tool Definition System

This document provides comprehensive documentation for the Tool Definition System in the OpenAI Agents Framework, as implemented in the todo application. The system enables AI agents to interact with application services through a well-defined, extensible architecture.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Pydantic-Based Tool Validation](#pydantic-based-tool-validation)
3. [Tool Registration and Discovery](#tool-registration-and-discovery)
4. [Argument Processing and Validation](#argument-processing-and-validation)
5. [Tool Execution Patterns](#tool-execution-patterns)
6. [Tool Categorization and Organization](#tool-categorization-and-organization)
7. [Tool Composition and Chaining](#tool-composition-and-chaining)
8. [Error Handling and Resilience](#error-handling-and-resilience)
9. [Performance Monitoring and Optimization](#performance-monitoring-and-optimization)
10. [Tool Testing and Validation](#tool-testing-and-validation)
11. [Custom Tool Creation Guidelines](#custom-tool-creation-guidelines)
12. [Advanced Patterns and Best Practices](#advanced-patterns-and-best-practices)

## Architecture Overview

The Tool Definition System follows a layered architecture that separates concerns between tool definition, implementation, registration, and execution:

### Core Components

```python
# High-level architecture
├── Tool Definitions Layer (tool_definitions.py)
│   ├── FunctionTool specifications
│   ├── JSON schema generation
│   └── Tool registry
├── Argument Models Layer (argument_models.py)
│   ├── Pydantic validation models
│   ├── Type safety enforcement
│   └── Schema generation
├── Implementation Layer (tool_implementations.py)
│   ├── Business logic execution
│   ├── Service integration
│   └── Error handling
├── Context Management Layer (tool_context.py)
│   ├── Dependency injection
│   ├── User session context
│   └── Service management
└── Universal Tools Layer (universal_tools.py)
    ├── Cross-domain utilities
    ├── System-level operations
    └── Shared functionality
```

### Design Principles

1. **Separation of Concerns**: Clear boundaries between tool definition, validation, and implementation
2. **Type Safety**: Strong typing through Pydantic models and TypeScript-like validation
3. **Extensibility**: Modular design supporting easy addition of new tools
4. **Context Awareness**: Tools have access to user context and services
5. **Error Resilience**: Comprehensive error handling and graceful failures
6. **Performance Optimized**: Efficient argument processing and caching

## Pydantic-Based Tool Validation

### Argument Models Architecture

The system uses Pydantic models to define strict validation schemas for tool arguments:

```python
# Example: CreateTodoArgs model
class CreateTodoArgs(BaseModel):
    item: str = Field(
        ...,
        description="The name/title of the todo item to create"
    )
    description: str | None = Field(
        default=None,
        description="The description/content of the todo item"
    )
    start_time: str = Field(
        ...,
        description="The start time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD"
    )
    end_time: str = Field(
        ...,
        description="The end time for the todo in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD"
    )
    tags: list[str] | None = Field(
        default=None,
        description="List of tag names to associate with the todo"
    )
    importance: str = Field(
        default="none",
        description="The importance level: none, low, medium, high"
    )
    timezone: str | None = Field(
        default=None,
        description="Timezone for date parsing (e.g., 'America/New_York')"
    )
```

### Schema Generation Process

1. **Automatic JSON Schema**: Pydantic automatically generates JSON schemas from model definitions
2. **OpenAI Compatibility**: Schemas are compatible with OpenAI's function calling format
3. **Type Validation**: Runtime validation of incoming arguments against defined types
4. **Custom Validators**: Support for custom validation logic through Pydantic validators

```python
# JSON schema generation example
def get_tool_definitions() -> Sequence[FunctionTool]:
    create_todo_tool = FunctionTool(
        name="create_todo",
        description="Create a new todo item using the TodoService.",
        params_json_schema=CreateTodoArgs.model_json_schema(),  # Auto-generated
        on_invoke_tool=create_todo_impl,
    )
    return [create_todo_tool]
```

### Advanced Validation Patterns

#### Custom Validators
```python
from pydantic import field_validator
from datetime import datetime

class ScheduleTodoArgs(BaseModel):
    target_date: str | None = Field(
        default=None,
        description="The target date for scheduling (YYYY-MM-DD)"
    )

    @field_validator('target_date')
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
```

#### Conditional Validation
```python
class UpdateTodoArgs(BaseModel):
    start_time: str | None = None
    end_time: str | None = None

    @model_validator(mode='after')
    def validate_time_ordering(self) -> 'UpdateTodoArgs':
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            if end <= start:
                raise ValueError("End time must be after start time")
        return self
```

## Tool Registration and Discovery

### Tool Definition Registry

The system maintains a centralized registry of all available tools:

```python
# tool_definitions.py
def get_tool_definitions() -> Sequence[FunctionTool]:
    """Return the list of FunctionTool definitions for the todo agent."""
    from agents import FunctionTool

    # Universal tools (always first)
    get_user_datetime_tool = FunctionTool(
        name="get_user_datetime",
        description="Get the user's current date, time, and timezone information",
        params_json_schema=GetUserDatetimeArgs.model_json_schema(),
        on_invoke_tool=get_user_datetime_impl,
    )

    # Domain-specific tools
    create_todo_tool = FunctionTool(
        name="create_todo",
        description="Create a new todo item using the TodoService",
        params_json_schema=CreateTodoArgs.model_json_schema(),
        on_invoke_tool=create_todo_impl,
    )

    return [
        get_user_datetime_tool,  # Universal tool first
        create_todo_tool,
        delete_todo_tool,
        update_todo_tool,
        # ... other tools
    ]
```

### Tool Categorization System

```python
class ToolCategory(Enum):
    """Categories for organizing tools by purpose and domain."""
    UNIVERSAL = "universal"      # Cross-domain utilities
    CRUD = "crud"               # Create, Read, Update, Delete operations
    SCHEDULING = "scheduling"    # Schedule analysis and management
    ANALYSIS = "analysis"        # Data analysis and insights
    SYSTEM = "system"           # System-level operations

# Tool categorization metadata
TOOL_METADATA = {
    "get_user_datetime": {
        "category": ToolCategory.UNIVERSAL,
        "priority": 1,
        "required_permissions": ["read_timezone"],
        "rate_limit": None,  # No rate limit for universal tools
    },
    "create_todo": {
        "category": ToolCategory.CRUD,
        "priority": 2,
        "required_permissions": ["write_todo"],
        "rate_limit": 50,  # 50 calls per hour
    },
    "schedule_todo": {
        "category": ToolCategory.SCHEDULING,
        "priority": 3,
        "required_permissions": ["write_todo", "read_schedule"],
        "rate_limit": 30,  # 30 calls per hour
    }
}
```

### Dynamic Tool Loading

```python
class ToolRegistry:
    """Dynamic tool registry with hot-reloading capabilities."""

    def __init__(self):
        self._tools: dict[str, FunctionTool] = {}
        self._metadata: dict[str, dict] = {}
        self._load_tools()

    def _load_tools(self) -> None:
        """Load all available tools from defined modules."""
        tool_modules = [
            "universal_tools",
            "todo_tools",
            "schedule_tools",
            "analysis_tools"
        ]

        for module_name in tool_modules:
            try:
                module = import_module(f".{module_name}", package=__package__)
                if hasattr(module, "get_tools"):
                    tools = module.get_tools()
                    for tool in tools:
                        self._tools[tool.name] = tool
            except ImportError as e:
                logger.warning(f"Failed to load tool module {module_name}: {e}")

    def get_tool(self, name: str) -> FunctionTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[FunctionTool]:
        """List all tools, optionally filtered by category."""
        if category is None:
            return list(self._tools.values())

        return [
            tool for tool in self._tools.values()
            if self._metadata.get(tool.name, {}).get("category") == category
        ]
```

## Argument Processing and Validation

### Preprocessing Pipeline

The system implements a sophisticated argument preprocessing pipeline to handle various input formats and edge cases:

```python
def _preprocess_args(args: str) -> str:
    """Preprocess tool arguments to handle double-encoded JSON arrays.

    Some LLMs may send array fields as stringified JSON within the JSON string,
    e.g., tags: '["study"]' instead of tags: ["study"].
    """
    try:
        data = json.loads(args)

        # Check if any field is a string that looks like a JSON array
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
                try:
                    # Try to parse it as JSON
                    parsed_array = json.loads(value)
                    if isinstance(parsed_array, list):
                        data[key] = parsed_array
                except (json.JSONDecodeError, ValueError):
                    # If it fails to parse, leave it as is
                    pass

        return json.dumps(data)
    except (json.JSONDecodeError, ValueError):
        # If we can't parse the args, return them as-is
        return args
```

### Type Conversion and Normalization

```python
class ArgumentProcessor:
    """Advanced argument processing with type conversion and validation."""

    @staticmethod
    def process_datetime_args(
        args: dict[str, Any],
        timezone: str | None = None
    ) -> dict[str, Any]:
        """Process and normalize datetime arguments."""
        user_tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
        processed = args.copy()

        datetime_fields = ['start_time', 'end_time', 'alarm_time', 'target_date']

        for field in datetime_fields:
            if field in processed and processed[field] is not None:
                processed[field] = ArgumentProcessor._parse_datetime(
                    processed[field], user_tz
                )

        return processed

    @staticmethod
    def _parse_datetime(date_str: str, timezone: ZoneInfo) -> datetime:
        """Parse datetime string with multiple format support."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone).astimezone(UTC)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse datetime: {date_str}")
```

### Validation Framework

```python
class ToolValidator:
    """Comprehensive validation framework for tool arguments."""

    def __init__(self, model: type[BaseModel]):
        self.model = model
        self.preprocessors = []
        self.postprocessors = []

    def add_preprocessor(self, processor: Callable[[dict], dict]) -> 'ToolValidator':
        """Add a preprocessing function."""
        self.preprocessors.append(processor)
        return self

    def add_postprocessor(self, processor: Callable[[BaseModel], BaseModel]) -> 'ToolValidator':
        """Add a postprocessing function."""
        self.postprocessors.append(processor)
        return self

    def validate(self, args: str | dict) -> BaseModel:
        """Validate and process arguments."""
        # Convert to dict if string
        if isinstance(args, str):
            try:
                data = json.loads(args)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON arguments: {args}")
        else:
            data = args.copy()

        # Apply preprocessors
        for processor in self.preprocessors:
            data = processor(data)

        # Validate with Pydantic
        try:
            model_instance = self.model.model_validate(data)
        except ValueError as e:
            raise ValueError(f"Validation failed: {e}")

        # Apply postprocessors
        for processor in self.postprocessors:
            model_instance = processor(model_instance)

        return model_instance

# Usage example
create_todo_validator = ToolValidator(CreateTodoArgs)\
    .add_preprocessor(lambda x: _preprocess_args(json.dumps(x)))\
    .add_preprocessor(lambda x: ArgumentProcessor.process_datetime_args(x, x.get('timezone')))\
    .add_postprocessor(lambda x: ArgumentProcessor.validate_business_rules(x))
```

## Tool Execution Patterns

### Execution Context Management

```python
class ToolExecutionContext:
    """Context manager for tool execution with proper resource management."""

    def __init__(self, user_id: UUID, services: dict[str, Any]):
        self.user_id = user_id
        self.services = services
        self._context_stack = []

    async def __aenter__(self) -> 'ToolExecutionContext':
        """Enter the execution context."""
        # Set up global context for tool implementations
        set_agent_context(
            todo_service=self.services.get('todo_service'),
            tag_service=self.services.get('tag_service'),
            user_id=self.user_id,
            quota_service=self.services.get('quota_service'),
            rate_limit_service=self.services.get('rate_limit_service'),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the execution context and cleanup resources."""
        # Cleanup context
        set_agent_context(None, None, None)

        # Log execution metrics
        if exc_type is not None:
            logger.error(f"Tool execution failed: {exc_val}")
        else:
            logger.debug(f"Tool execution completed for user {self.user_id}")
```

### Async Tool Implementation Pattern

```python
async def create_todo_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the create_todo function."""
    # Get context
    todo_service = get_todo_service()
    tag_service = get_tag_service()
    current_user_id = get_current_user_id()

    # Validate context
    if not todo_service or not tag_service or not current_user_id:
        return "Error: Agent context not properly initialized"

    # Process arguments
    try:
        args = _preprocess_args(args)
        parsed = CreateTodoArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments: {e}"

    # Execute business logic
    try:
        todo = await _create_todo_with_validation(
            todo_service, tag_service, parsed, current_user_id
        )
        return f"Successfully created todo '{todo.item}' (ID: {todo.id})"
    except Exception as e:
        return f"Error creating todo: {e}"
```

### Transaction Management

```python
class TransactionalToolExecutor:
    """Tool executor with transaction management."""

    def __init__(self, tool_func: Callable):
        self.tool_func = tool_func

    async def execute(self, ctx: RunContextWrapper, args: str) -> str:
        """Execute tool with transaction support."""
        todo_service = get_todo_service()
        session = getattr(todo_service.repository, "session", None)

        if session is None:
            # Non-transactional execution
            return await self.tool_func(ctx, args)

        try:
            # Begin transaction
            async with session.begin_nested():
                result = await self.tool_func(ctx, args)
                # Will be committed if no exception
                return result
        except Exception as e:
            # Transaction automatically rolled back
            logger.error(f"Tool execution failed and rolled back: {e}")
            return f"Error: {e}"
```

### Tool Composition Pattern

```python
class ComposedTool:
    """Tool that combines multiple operations."""

    def __init__(self, tools: list[FunctionTool], composition_logic: Callable):
        self.tools = tools
        self.composition_logic = composition_logic

    async def execute(self, ctx: RunContextWrapper, args: str) -> str:
        """Execute composed tool workflow."""
        try:
            # Parse arguments
            parsed_args = json.loads(args)

            # Execute composition logic
            result = await self.composition_logic(self.tools, parsed_args, ctx)

            return result
        except Exception as e:
            return f"Composition failed: {e}"

# Example: Schedule and create todo in one operation
async def schedule_and_create_workflow(
    tools: list[FunctionTool],
    args: dict[str, Any],
    ctx: RunContextWrapper
) -> str:
    """Workflow that analyzes schedule and creates optimal todo."""

    # First analyze schedule
    schedule_analyzer = next(t for t in tools if t.name == "analyze_schedule")
    schedule_result = await schedule_analyzer.on_invoke_tool(ctx, json.dumps({
        "target_date": args.get("target_date"),
        "timezone": args.get("timezone")
    }))

    # Then create todo with optimal timing
    todo_creator = next(t for t in tools if t.name == "schedule_todo")
    todo_result = await todo_creator.on_invoke_tool(ctx, json.dumps(args))

    return f"Schedule Analysis:\n{schedule_result}\n\nTodo Creation:\n{todo_result}"
```

## Tool Categorization and Organization

### Category-Based Architecture

```python
class ToolCategory:
    """Base class for tool categories."""

    def __init__(self, name: str, description: str, priority: int = 0):
        self.name = name
        self.description = description
        self.priority = priority
        self.tools: dict[str, FunctionTool] = {}

    def register_tool(self, tool: FunctionTool) -> None:
        """Register a tool in this category."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> FunctionTool | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> list[FunctionTool]:
        """List all tools in this category."""
        return list(self.tools.values())

# Predefined categories
UNIVERSAL_CATEGORY = ToolCategory(
    name="universal",
    description="Cross-domain utilities available to all agents",
    priority=1
)

CRUD_CATEGORY = ToolCategory(
    name="crud",
    description="Create, Read, Update, Delete operations",
    priority=2
)

SCHEDULING_CATEGORY = ToolCategory(
    name="scheduling",
    description="Schedule analysis and time management",
    priority=3
)

ANALYSIS_CATEGORY = ToolCategory(
    name="analysis",
    description="Data analysis and insights generation",
    priority=4
)
```

### Hierarchical Organization

```python
class ToolRegistry:
    """Hierarchical tool registry with category support."""

    def __init__(self):
        self.categories: dict[str, ToolCategory] = {}
        self._initialize_categories()
        self._register_tools()

    def _initialize_categories(self) -> None:
        """Initialize standard categories."""
        self.categories.update({
            "universal": UNIVERSAL_CATEGORY,
            "crud": CRUD_CATEGORY,
            "scheduling": SCHEDULING_CATEGORY,
            "analysis": ANALYSIS_CATEGORY,
        })

    def _register_tools(self) -> None:
        """Register all tools in their appropriate categories."""
        # Register universal tools
        self.categories["universal"].register_tool(FunctionTool(
            name="get_user_datetime",
            description="Get user's current date and time",
            params_json_schema=GetUserDatetimeArgs.model_json_schema(),
            on_invoke_tool=get_user_datetime_impl,
        ))

        # Register CRUD tools
        self.categories["crud"].register_tool(FunctionTool(
            name="create_todo",
            description="Create a new todo item",
            params_json_schema=CreateTodoArgs.model_json_schema(),
            on_invoke_tool=create_todo_impl,
        ))

        # ... register other tools

    def get_tools_by_category(self, category_name: str) -> list[FunctionTool]:
        """Get all tools in a specific category."""
        category = self.categories.get(category_name)
        return category.list_tools() if category else []

    def get_all_tools(self) -> dict[str, list[FunctionTool]]:
        """Get all tools organized by category."""
        return {
            name: category.list_tools()
            for name, category in self.categories.items()
        }
```

### Tag-Based Organization

```python
class ToolTagger:
    """Tag-based organization for tools."""

    # Standard tags
    STANDARD_TAGS = {
        "read_only": "Tool that only reads data",
        "write": "Tool that modifies data",
        "async": "Tool that performs async operations",
        "transactional": "Tool that requires database transactions",
        "rate_limited": "Tool with rate limiting",
        "requires_auth": "Tool that requires user authentication",
        "time_sensitive": "Tool that deals with time-based operations",
        "resource_intensive": "Tool that consumes significant resources"
    }

    def __init__(self):
        self.tool_tags: dict[str, set[str]] = {}
        self._initialize_tags()

    def _initialize_tags(self) -> None:
        """Initialize standard tool tags."""
        self.tool_tags.update({
            "get_user_datetime": {"read_only", "async", "time_sensitive"},
            "get_user_quota": {"read_only", "async", "requires_auth"},
            "create_todo": {"write", "async", "transactional", "rate_limited"},
            "update_todo": {"write", "async", "transactional", "rate_limited"},
            "delete_todo": {"write", "async", "transactional", "rate_limited"},
            "analyze_schedule": {"read_only", "async", "time_sensitive", "resource_intensive"},
            "schedule_todo": {"write", "async", "transactional", "rate_limited", "time_sensitive"},
        })

    def get_tools_by_tag(self, tag: str) -> list[str]:
        """Get all tools with a specific tag."""
        return [
            tool_name for tool_name, tags in self.tool_tags.items()
            if tag in tags
        ]

    def add_tag(self, tool_name: str, tag: str) -> None:
        """Add a tag to a tool."""
        if tool_name not in self.tool_tags:
            self.tool_tags[tool_name] = set()
        self.tool_tags[tool_name].add(tag)
```

## Error Handling and Resilience

### Comprehensive Error Handling Strategy

```python
class ToolErrorHandler:
    """Advanced error handling for tool execution."""

    def __init__(self):
        self.error_handlers = {
            ValidationError: self._handle_validation_error,
            AuthenticationError: self._handle_auth_error,
            RateLimitError: self._handle_rate_limit_error,
            DatabaseError: self._handle_database_error,
            ServiceUnavailableError: self._handle_service_error,
            TimeoutError: self._handle_timeout_error,
        }

    async def handle_error(
        self,
        error: Exception,
        tool_name: str,
        args: str
    ) -> str:
        """Handle tool execution errors with appropriate responses."""
        error_type = type(error)
        handler = self.error_handlers.get(error_type, self._handle_generic_error)

        # Log the error
        logger.error(
            f"Tool execution error in {tool_name}: {error}",
            extra={"tool": tool_name, "args": args, "error_type": error_type.__name__}
        )

        # Handle the error
        return await handler(error, tool_name, args)

    async def _handle_validation_error(self, error: Exception, tool_name: str, args: str) -> str:
        """Handle validation errors with helpful messages."""
        return f"❌ Invalid input for {tool_name}: {error}. Please check your input and try again."

    async def _handle_auth_error(self, error: Exception, tool_name: str, args: str) -> str:
        """Handle authentication errors."""
        return f"🔐 Authentication required for {tool_name}. Please log in and try again."

    async def _handle_rate_limit_error(self, error: Exception, tool_name: str, args: str) -> str:
        """Handle rate limiting errors."""
        return f"⏱️ Rate limit exceeded for {tool_name}. Please wait before trying again."

    async def _handle_database_error(self, error: Exception, tool_name: str, args: str) -> str:
        """Handle database errors."""
        return f"💾 Database error in {tool_name}. Please try again later."

    async def _handle_generic_error(self, error: Exception, tool_name: str, args: str) -> str:
        """Handle unexpected errors."""
        return f"⚠️ Unexpected error in {tool_name}. The issue has been logged and we're working on it."
```

### Retry Mechanism

```python
class RetryableToolExecutor:
    """Tool executor with intelligent retry mechanism."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retryable_exceptions = {
            DatabaseError,
            ServiceUnavailableError,
            TimeoutError,
        }

    async def execute_with_retry(
        self,
        tool_func: Callable,
        ctx: RunContextWrapper,
        args: str
    ) -> str:
        """Execute tool with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await tool_func(ctx, args)
            except Exception as e:
                last_exception = e

                # Don't retry non-retryable exceptions
                if type(e) not in self.retryable_exceptions:
                    raise e

                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(
                        f"Tool execution failed (attempt {attempt + 1}), retrying in {delay}s",
                        extra={"error": str(e), "attempt": attempt + 1}
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Tool execution failed after {self.max_retries} retries",
                        extra={"error": str(e)}
                    )

        raise last_exception
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker for tool execution to prevent cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.timeout
        )

    def _on_success(self) -> None:
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self) -> None:
        """Handle execution failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

## Performance Monitoring and Optimization

### Performance Metrics Collection

```python
class ToolPerformanceMonitor:
    """Monitor and collect performance metrics for tool execution."""

    def __init__(self):
        self.metrics: dict[str, dict] = {}
        self.active_operations: dict[str, float] = {}

    def start_operation(self, tool_name: str, operation_id: str) -> None:
        """Start monitoring an operation."""
        self.active_operations[operation_id] = {
            "tool_name": tool_name,
            "start_time": time.time(),
        }

    def end_operation(self, operation_id: str, success: bool = True) -> None:
        """End monitoring an operation and record metrics."""
        if operation_id not in self.active_operations:
            return

        op_data = self.active_operations.pop(operation_id)
        tool_name = op_data["tool_name"]
        duration = time.time() - op_data["start_time"]

        if tool_name not in self.metrics:
            self.metrics[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
            }

        metrics = self.metrics[tool_name]
        metrics["total_calls"] += 1
        metrics["total_duration"] += duration
        metrics["avg_duration"] = metrics["total_duration"] / metrics["total_calls"]
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)

        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1

    def get_metrics(self, tool_name: str) -> dict | None:
        """Get performance metrics for a tool."""
        return self.metrics.get(tool_name)

    def get_all_metrics(self) -> dict[str, dict]:
        """Get performance metrics for all tools."""
        return self.metrics.copy()
```

### Performance Optimization Strategies

```python
class OptimizedToolExecutor:
    """Tool executor with performance optimizations."""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.performance_monitor = ToolPerformanceMonitor()

    async def execute_optimized(
        self,
        tool_func: Callable,
        tool_name: str,
        ctx: RunContextWrapper,
        args: str
    ) -> str:
        """Execute tool with optimizations."""
        operation_id = str(uuid.uuid4())
        self.performance_monitor.start_operation(tool_name, operation_id)

        try:
            # Check cache for read-only operations
            if self._is_readonly_operation(tool_name):
                cached_result = self._get_cached_result(tool_name, args)
                if cached_result:
                    self.performance_monitor.end_operation(operation_id, True)
                    return cached_result

            # Execute the tool
            result = await tool_func(ctx, args)

            # Cache read-only results
            if self._is_readonly_operation(tool_name):
                self._cache_result(tool_name, args, result)

            self.performance_monitor.end_operation(operation_id, True)
            return result

        except Exception as e:
            self.performance_monitor.end_operation(operation_id, False)
            raise e

    def _is_readonly_operation(self, tool_name: str) -> bool:
        """Check if a tool operation is read-only."""
        readonly_tools = {
            "get_user_datetime",
            "get_user_quota",
            "get_todo_list",
            "analyze_schedule"
        }
        return tool_name in readonly_tools

    def _get_cache_key(self, tool_name: str, args: str) -> str:
        """Generate cache key for tool arguments."""
        return f"{tool_name}:{hash(args)}"

    def _get_cached_result(self, tool_name: str, args: str) -> str | None:
        """Get cached result if available and not expired."""
        cache_key = self._get_cache_key(tool_name, args)
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["result"]
            else:
                del self.cache[cache_key]
        return None

    def _cache_result(self, tool_name: str, args: str, result: str) -> None:
        """Cache tool execution result."""
        cache_key = self._get_cache_key(tool_name, args)
        self.cache[cache_key] = {
            "result": result,
            "timestamp": time.time()
        }
```

### Resource Usage Monitoring

```python
class ResourceMonitor:
    """Monitor resource usage during tool execution."""

    def __init__(self):
        self.memory_usage = {}
        self.cpu_usage = {}

    @contextmanager
    def monitor_execution(self, tool_name: str):
        """Context manager for monitoring resource usage."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Record initial metrics
        initial_memory = process.memory_info().rss
        initial_cpu = process.cpu_percent()

        start_time = time.time()

        try:
            yield
        finally:
            # Record final metrics
            final_memory = process.memory_info().rss
            final_cpu = process.cpu_percent()
            duration = time.time() - start_time

            # Calculate usage
            memory_delta = final_memory - initial_memory
            avg_cpu = (initial_cpu + final_cpu) / 2

            # Store metrics
            if tool_name not in self.memory_usage:
                self.memory_usage[tool_name] = []
                self.cpu_usage[tool_name] = []

            self.memory_usage[tool_name].append({
                "delta": memory_delta,
                "duration": duration
            })

            self.cpu_usage[tool_name].append({
                "usage": avg_cpu,
                "duration": duration
            })

    def get_resource_report(self) -> dict:
        """Get comprehensive resource usage report."""
        return {
            "memory": {
                tool: {
                    "total_delta": sum(m["delta"] for m in metrics),
                    "avg_delta": sum(m["delta"] for m in metrics) / len(metrics),
                    "call_count": len(metrics)
                }
                for tool, metrics in self.memory_usage.items()
            },
            "cpu": {
                tool: {
                    "avg_usage": sum(m["usage"] for m in metrics) / len(metrics),
                    "call_count": len(metrics)
                }
                for tool, metrics in self.cpu_usage.items()
            }
        }
```

## Tool Testing and Validation

### Unit Testing Framework

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class ToolTestCase:
    """Base class for tool testing."""

    def setup_method(self):
        """Set up test environment."""
        self.mock_todo_service = AsyncMock()
        self.mock_tag_service = AsyncMock()
        self.mock_quota_service = AsyncMock()
        self.mock_rate_limit_service = AsyncMock()

        # Set up context
        set_agent_context(
            todo_service=self.mock_todo_service,
            tag_service=self.mock_tag_service,
            user_id=UUID("12345678-1234-5678-1234-567812345678"),
            quota_service=self.mock_quota_service,
            rate_limit_service=self.mock_rate_limit_service,
        )

    def teardown_method(self):
        """Clean up test environment."""
        set_agent_context(None, None, None)

class TestCreateTodoTool(ToolTestCase):
    """Test cases for create_todo tool."""

    @pytest.mark.asyncio
    async def test_create_todo_success(self):
        """Test successful todo creation."""
        # Arrange
        args = json.dumps({
            "item": "Test Todo",
            "description": "Test Description",
            "start_time": "2024-01-01 10:00:00",
            "end_time": "2024-01-01 11:00:00",
            "importance": "high",
            "tags": ["work", "important"]
        })

        mock_todo = MagicMock()
        mock_todo.id = UUID("12345678-1234-5678-1234-567812345679")
        mock_todo.item = "Test Todo"

        self.mock_todo_service.create.return_value = mock_todo
        self.mock_todo_service.repository.session = MagicMock()

        # Act
        result = await create_todo_impl(None, args)

        # Assert
        assert "Successfully created todo 'Test Todo'" in result
        self.mock_todo_service.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_todo_validation_error(self):
        """Test todo creation with invalid arguments."""
        # Arrange
        args = json.dumps({
            "item": "",  # Empty item should cause validation error
            "start_time": "2024-01-01 10:00:00",
            "end_time": "2024-01-01 09:00:00",  # End before start
        })

        # Act
        result = await create_todo_impl(None, args)

        # Assert
        assert "Error" in result or "Invalid" in result

    @pytest.mark.asyncio
    async def test_create_todo_time_conflict(self):
        """Test todo creation with time conflict."""
        # Arrange
        args = json.dumps({
            "item": "Conflicting Todo",
            "start_time": "2024-01-01 10:00:00",
            "end_time": "2024-01-01 11:00:00",
        })

        # Mock conflict detection
        self.mock_todo_service.check_time_conflict.return_value = [
            MagicMock(item="Existing Todo")
        ]

        # Act
        result = await create_todo_impl(None, args)

        # Assert
        assert "conflict" in result.lower()
```

### Integration Testing

```python
class ToolIntegrationTest:
    """Integration tests for tool interactions."""

    @pytest.mark.asyncio
    async def test_schedule_analyze_create_workflow(self):
        """Test complete workflow from schedule analysis to todo creation."""
        # This test requires actual services or comprehensive mocks
        pass

    @pytest.mark.asyncio
    async def test_tool_error_propagation(self):
        """Test error handling across tool chains."""
        pass

class PerformanceTest:
    """Performance tests for tool execution."""

    @pytest.mark.asyncio
    async def test_tool_execution_time(self):
        """Test tool execution within acceptable time limits."""
        pass

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent tool execution performance."""
        pass
```

### Property-Based Testing

```python
import hypothesis
from hypothesis import given, strategies as st

class ToolPropertyTests:
    """Property-based tests for tool behavior."""

    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.asyncio
    async def test_todo_item_validation(self, item_text):
        """Test todo item validation with various inputs."""
        args = json.dumps({
            "item": item_text,
            "start_time": "2024-01-01 10:00:00",
            "end_time": "2024-01-01 11:00:00",
        })

        # Test that valid items pass validation
        # Test that items with only whitespace fail validation
        pass

    @given(st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2024, 12, 31)))
    @pytest.mark.asyncio
    async def test_datetime_parsing(self, dt):
        """Test datetime parsing with various formats."""
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        # Test that valid datetime strings parse correctly
        pass
```

## Custom Tool Creation Guidelines

### Tool Creation Template

```python
"""
Template for creating new custom tools.
Follow this pattern to ensure consistency and proper integration.
"""

from typing import TYPE_CHECKING
from agents import RunContextWrapper

if TYPE_CHECKING:
    from collections.abc import Sequence
    from agents import FunctionTool

# 1. Define argument model
class CustomToolArgs(BaseModel):
    """Argument model for custom tool."""

    required_param: str = Field(
        ...,
        description="Required parameter description"
    )
    optional_param: str | None = Field(
        default=None,
        description="Optional parameter description"
    )
    timezone: str | None = Field(
        default=None,
        description="Timezone for time-based operations"
    )

# 2. Implement the tool function
async def custom_tool_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the custom tool.

    Args:
        ctx: Runtime context wrapper
        args: JSON string containing tool arguments

    Returns:
        String response with operation result
    """
    # Get context services
    service = get_service()
    current_user_id = get_current_user_id()

    if not service or not current_user_id:
        return "Error: Agent context not properly initialized"

    # Validate and parse arguments
    try:
        args = _preprocess_args(args)
        parsed = CustomToolArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments: {e}"

    # Execute business logic
    try:
        result = await perform_custom_operation(
            service, current_user_id, parsed
        )
        return f"Successfully completed custom operation: {result}"
    except Exception as e:
        return f"Error performing custom operation: {e}"

# 3. Add to tool definitions
def add_custom_tool(tools: list[FunctionTool]) -> list[FunctionTool]:
    """Add custom tool to tool definitions."""
    from agents import FunctionTool

    custom_tool = FunctionTool(
        name="custom_tool",
        description="Description of what the custom tool does",
        params_json_schema=CustomToolArgs.model_json_schema(),
        on_invoke_tool=custom_tool_impl,
    )

    return tools + [custom_tool]

# 4. Helper functions
async def perform_custom_operation(
    service: Any,
    user_id: UUID,
    args: CustomToolArgs
) -> str:
    """Perform the actual custom operation."""
    # Implement your custom logic here
    pass
```

### Best Practices for Tool Development

#### 1. Input Validation
```python
# Always validate inputs thoroughly
def validate_inputs(args: CustomToolArgs) -> None:
    """Validate tool arguments."""
    if not args.required_param.strip():
        raise ValueError("Required parameter cannot be empty")

    if args.optional_param and len(args.optional_param) > 1000:
        raise ValueError("Optional parameter too long")
```

#### 2. Error Handling
```python
# Implement comprehensive error handling
async def safe_operation(service: Any, args: CustomToolArgs) -> str:
    """Perform operation with proper error handling."""
    try:
        # Business logic
        result = await service.do_something(args)
        return f"Success: {result}"
    except ValidationError as e:
        return f"Validation error: {e}"
    except PermissionError as e:
        return f"Permission denied: {e}"
    except Exception as e:
        logger.exception("Unexpected error in custom tool")
        return f"Unexpected error: Operation failed"
```

#### 3. Resource Management
```python
# Proper resource management
async def resource_aware_operation(args: CustomToolArgs) -> str:
    """Operation with proper resource management."""
    async with resource_manager:
        try:
            result = await expensive_operation(args)
            return result
        finally:
            # Cleanup resources
            await cleanup_resources()
```

#### 4. Logging and Monitoring
```python
# Comprehensive logging
import structlog

logger = structlog.get_logger()

async def monitored_operation(args: CustomToolArgs) -> str:
    """Operation with monitoring and logging."""
    operation_id = str(uuid.uuid4())

    logger.info("Starting custom tool operation",
                operation_id=operation_id,
                args=args.dict())

    try:
        result = await perform_operation(args)
        logger.info("Custom tool operation completed successfully",
                    operation_id=operation_id)
        return result
    except Exception as e:
        logger.error("Custom tool operation failed",
                     operation_id=operation_id,
                     error=str(e))
        raise
```

#### 5. Testing Strategy
```python
# Comprehensive testing
class CustomToolTest(ToolTestCase):
    """Test suite for custom tool."""

    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test successful tool operation."""
        pass

    @pytest.mark.asyncio
    async def test_validation_errors(self):
        """Test various validation error scenarios."""
        pass

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling capabilities."""
        pass

    @pytest.mark.asyncio
    async def test_performance(self):
        """Test tool performance characteristics."""
        pass
```

## Advanced Patterns and Best Practices

### Plugin Architecture

```python
class ToolPlugin:
    """Base class for tool plugins."""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    def get_tools(self) -> list[FunctionTool]:
        """Get tools provided by this plugin."""
        raise NotImplementedError

    def get_dependencies(self) -> list[str]:
        """Get list of required dependencies."""
        return []

    def initialize(self, context: dict) -> None:
        """Initialize plugin with context."""
        pass

class PluginManager:
    """Manager for tool plugins."""

    def __init__(self):
        self.plugins: dict[str, ToolPlugin] = {}

    def register_plugin(self, plugin: ToolPlugin) -> None:
        """Register a new plugin."""
        self.plugins[plugin.name] = plugin

    def load_plugin(self, plugin_path: str) -> None:
        """Load plugin from file."""
        # Dynamic plugin loading logic
        pass

    def get_all_tools(self) -> list[FunctionTool]:
        """Get all tools from all registered plugins."""
        tools = []
        for plugin in self.plugins.values():
            tools.extend(plugin.get_tools())
        return tools
```

### Tool Composition DSL

```python
class ToolWorkflowBuilder:
    """Domain-specific language for building tool workflows."""

    def __init__(self):
        self.steps = []

    def tool(self, name: str, args: dict | None = None) -> 'ToolWorkflowBuilder':
        """Add a tool step to the workflow."""
        self.steps.append({
            "type": "tool",
            "name": name,
            "args": args or {}
        })
        return self

    def condition(self, condition: Callable, true_branch: 'ToolWorkflowBuilder', false_branch: 'ToolWorkflowBuilder' = None) -> 'ToolWorkflowBuilder':
        """Add a conditional step."""
        self.steps.append({
            "type": "condition",
            "condition": condition,
            "true_branch": true_branch.steps,
            "false_branch": false_branch.steps if false_branch else None
        })
        return self

    def parallel(self, *branches: 'ToolWorkflowBuilder') -> 'ToolWorkflowBuilder':
        """Add parallel execution steps."""
        self.steps.append({
            "type": "parallel",
            "branches": [branch.steps for branch in branches]
        })
        return self

    def build(self) -> 'ToolWorkflow':
        """Build the workflow."""
        return ToolWorkflow(self.steps)

class ToolWorkflow:
    """Executable tool workflow."""

    def __init__(self, steps: list[dict]):
        self.steps = steps

    async def execute(self, ctx: RunContextWrapper, initial_args: str) -> str:
        """Execute the workflow."""
        current_context = json.loads(initial_args)

        for step in self.steps:
            if step["type"] == "tool":
                tool_name = step["name"]
                tool_args = {**current_context, **step["args"]}

                # Execute tool
                tool = get_tool(tool_name)
                result = await tool.on_invoke_tool(ctx, json.dumps(tool_args))

                # Update context
                current_context[f"{tool_name}_result"] = result

            elif step["type"] == "condition":
                # Implement conditional logic
                pass

            elif step["type"] == "parallel":
                # Implement parallel execution
                pass

        return json.dumps(current_context)

# Usage example
workflow = (ToolWorkflowBuilder()
    .tool("get_user_datetime", {"timezone": "America/New_York"})
    .tool("analyze_schedule", {"include_days": 3})
    .condition(
        lambda ctx: "free_slots" in ctx,
        ToolWorkflowBuilder().tool("schedule_todo", {"target_date": "tomorrow"}),
        ToolWorkflowBuilder().tool("analyze_schedule", {"include_days": 7})
    )
    .build())

result = await workflow.execute(ctx, args)
```

### Tool Analytics and Insights

```python
class ToolAnalytics:
    """Analytics system for tool usage and performance."""

    def __init__(self):
        self.usage_data = {}
        self.performance_data = {}
        self.error_patterns = {}

    def record_usage(self, tool_name: str, user_id: UUID, args: dict, result: str) -> None:
        """Record tool usage for analytics."""
        timestamp = datetime.now(UTC)

        if tool_name not in self.usage_data:
            self.usage_data[tool_name] = []

        self.usage_data[tool_name].append({
            "user_id": str(user_id),
            "timestamp": timestamp,
            "args_hash": hash(json.dumps(args, sort_keys=True)),
            "result_length": len(result),
            "success": not result.startswith("Error")
        })

    def generate_insights(self) -> dict:
        """Generate insights from usage data."""
        insights = {}

        for tool_name, usage in self.usage_data.items():
            total_usage = len(usage)
            success_rate = sum(1 for u in usage if u["success"]) / total_usage

            # Most common usage patterns
            args_patterns = {}
            for u in usage:
                pattern = u["args_hash"]
                args_patterns[pattern] = args_patterns.get(pattern, 0) + 1

            insights[tool_name] = {
                "total_usage": total_usage,
                "success_rate": success_rate,
                "most_common_patterns": sorted(
                    args_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "usage_trend": self._calculate_usage_trend(usage)
            }

        return insights

    def _calculate_usage_trend(self, usage: list[dict]) -> str:
        """Calculate usage trend over time."""
        if len(usage) < 2:
            return "insufficient_data"

        # Group by day
        daily_usage = {}
        for u in usage:
            day = u["timestamp"].date()
            daily_usage[day] = daily_usage.get(day, 0) + 1

        # Simple trend calculation
        days = sorted(daily_usage.keys())
        if len(days) < 7:
            return "insufficient_data"

        recent_avg = sum(daily_usage[day] for day in days[-7:]) / 7
        earlier_avg = sum(daily_usage[day] for day in days[-14:-7]) / 7 if len(days) >= 14 else recent_avg

        if recent_avg > earlier_avg * 1.2:
            return "increasing"
        elif recent_avg < earlier_avg * 0.8:
            return "decreasing"
        else:
            return "stable"
```

### Tool Security and Access Control

```python
class ToolSecurityManager:
    """Security manager for tool access control."""

    def __init__(self):
        self.permission_map = {
            "create_todo": ["todo:create"],
            "update_todo": ["todo:update", "todo:read"],
            "delete_todo": ["todo:delete", "todo:read"],
            "get_todo_list": ["todo:read"],
            "analyze_schedule": ["schedule:read", "todo:read"],
            "schedule_todo": ["todo:create", "schedule:write"],
        }

    def check_permission(self, tool_name: str, user_permissions: set[str]) -> bool:
        """Check if user has permission to use a tool."""
        required_permissions = self.permission_map.get(tool_name, [])
        return all(perm in user_permissions for perm in required_permissions)

    def sanitize_args(self, tool_name: str, args: dict) -> dict:
        """Sanitize tool arguments for security."""
        sanitized = args.copy()

        # Remove potentially dangerous fields
        dangerous_fields = ["user_id", "session_id", "auth_token"]
        for field in dangerous_fields:
            sanitized.pop(field, None)

        # Apply tool-specific sanitization
        if tool_name in ["create_todo", "update_todo"]:
            # Sanitize HTML/SQL injection attempts
            for text_field in ["item", "description"]:
                if text_field in sanitized:
                    sanitized[text_field] = self._sanitize_text(sanitized[text_field])

        return sanitized

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text input."""
        import html
        # Basic HTML escaping
        return html.escape(text)
```

This comprehensive documentation covers all aspects of the Tool Definition System, providing detailed examples, patterns, and best practices for creating, managing, and optimizing AI agent tools. The system is designed to be extensible, secure, and performant while maintaining clean separation of concerns and providing excellent developer experience.