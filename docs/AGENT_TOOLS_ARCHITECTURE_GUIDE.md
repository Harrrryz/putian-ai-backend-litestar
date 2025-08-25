# Agent Tools Architecture Guide

## Overview

This guide documents the architecture and development patterns for AI agent tools in the `src/app/domain/todo_agents/tools/` folder. This modular structure serves as a blueprint for creating new agent tools and maintaining clean, scalable code organization.

## 🏗️ Architecture Philosophy

The tools architecture follows these core principles:

- **Separation of Concerns**: Each file has a single, well-defined responsibility
- **Type Safety**: Strong typing with Pydantic models for validation
- **Modularity**: Easy to extend with new tools without affecting existing ones
- **Testability**: Clean dependency injection and context management
- **Agent Framework Integration**: Seamless integration with the agents framework

## 📁 Folder Structure

```
tools/
├── __init__.py                  # Public API exports
├── agent_factory.py            # Agent creation and configuration
├── argument_models.py           # Pydantic models for tool arguments
├── system_instructions.py       # Agent behavior instructions
├── tool_context.py             # Global context management
├── tool_definitions.py         # Tool schema definitions
├── tool_implementations.py     # Tool business logic
└── __pycache__/                # Python bytecode cache
```

## 📋 File-by-File Documentation

### `__init__.py` - Public API Gateway

**Purpose**: Defines the public interface for the tools module.

```python
"""Todo agent tools module.

This module contains all the tool-related components for todo agents,
organized into focused modules for better maintainability.
"""

from .agent_factory import get_todo_agent
from .tool_definitions import get_tool_definitions

__all__ = [
    "get_todo_agent",
    "get_tool_definitions", 
]
```

**Guidelines**:
- Only export what external modules need
- Keep imports minimal and focused
- Include clear module docstring

### `agent_factory.py` - Agent Configuration Hub

**Purpose**: Creates and configures AI agents with tools and models.

**Key Components**:
- Model configuration (OpenAI/Volcengine integration)
- Tool registration and binding
- Agent instantiation with instructions

**Architecture Pattern**:
```python
def get_todo_agent() -> Agent:
    """Create and return a configured todo agent with all tools."""
    # 1. Configure AI model with API credentials
    # 2. Get tool definitions 
    # 3. Create agent with instructions and tools
    # 4. Return configured agent
```

**Extension Points**:
- Add new AI model providers
- Modify agent configuration
- Add agent-level middleware

### `argument_models.py` - Data Validation Layer

**Purpose**: Defines Pydantic models for tool argument validation and serialization.

**Structure Pattern**:
```python
class ToolNameArgs(BaseModel):
    """Arguments for tool_name function."""
    
    required_field: str = Field(..., description="Description")
    optional_field: str | None = Field(
        default=None, 
        description="Optional field description"
    )
    typed_field: int = Field(
        default=60, 
        description="Field with default value"
    )
```

**Best Practices**:
- Use descriptive field names and documentation
- Provide sensible defaults
- Include validation constraints
- Support optional fields with `None` defaults
- Use union types for flexibility (`str | None`)

**Current Models**:
- `CreateTodoArgs` - Todo creation parameters
- `UpdateTodoArgs` - Todo modification parameters  
- `DeleteTodoArgs` - Todo deletion parameters
- `GetTodoListArgs` - List filtering parameters
- `ScheduleTodoArgs` - Smart scheduling parameters
- `AnalyzeScheduleArgs` - Schedule analysis parameters
- `BatchUpdateScheduleArgs` - Bulk update parameters

### `system_instructions.py` - Agent Behavior Guide

**Purpose**: Contains comprehensive instructions that guide agent behavior and capabilities.

**Structure**:
```python
TODO_SYSTEM_INSTRUCTIONS = f"""
You are a personal todo assistant...

Core Capabilities:
1. Create, read, update, and delete todo items
2. Intelligent schedule analysis...

Todo Operations with Conflict Prevention:
When creating todos:
- Parse user's requests...
- AUTOMATIC CONFLICT DETECTION...

Current date: {datetime.now(tz=UTC).strftime('%Y-%m-%d')}
"""
```

**Content Guidelines**:
- Define agent persona and role
- List core capabilities clearly
- Provide detailed operational instructions
- Include conflict resolution strategies  
- Use dynamic content (current date)
- Specify error handling approaches
- Include security guidelines (no UUID exposure)

### `tool_context.py` - Context Management

**Purpose**: Manages global state and dependency injection for tool implementations.

**Architecture Pattern**:
```python
# Global context variables
_service_instance: Service | None = None
_current_user_id: UUID | None = None

def set_agent_context(service: Service, user_id: UUID) -> None:
    """Inject dependencies for tool execution."""
    
def get_service() -> Service | None:
    """Access service instance."""
```

**Benefits**:
- Clean dependency injection
- Avoids passing context through every function call
- Thread-safe per-request context
- Easy testing with context mocking

**Context Variables**:
- `_todo_service` - Todo business logic service
- `_tag_service` - Tag management service  
- `_current_user_id` - Current user identifier

### `tool_definitions.py` - Tool Schema Registry

**Purpose**: Defines FunctionTool schemas that connect argument models to implementations.

**Registration Pattern**:
```python
def get_tool_definitions() -> Sequence[FunctionTool]:
    """Return tool definitions for agent registration."""
    
    tool_name = FunctionTool(
        name="tool_name",
        description="What this tool does",
        params_json_schema=ToolArgs.model_json_schema(),
        on_invoke_tool=tool_implementation_function,
    )
    
    return [tool_name, ...]
```

**Components**:
- **name**: Tool identifier for agent
- **description**: AI-readable tool purpose
- **params_json_schema**: Pydantic model schema
- **on_invoke_tool**: Implementation function reference

### `tool_implementations.py` - Business Logic Core

**Purpose**: Contains the actual implementation functions with business logic.

**Implementation Pattern**:
```python
async def tool_name_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the tool_name function."""
    
    # 1. Get services and context
    service = get_service()
    user_id = get_current_user_id()
    
    # 2. Validate context
    if not service or not user_id:
        return "Error: Agent context not properly initialized"
    
    # 3. Parse and validate arguments
    try:
        parsed = ToolArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments: {e}"
    
    # 4. Execute business logic
    try:
        result = await service.operation(parsed.field)
        return f"Success: {result.description}"
    except Exception as e:
        return f"Error: {e}"
```

**Error Handling Standards**:
- Always validate context initialization
- Use try/catch for argument parsing
- Handle business logic exceptions gracefully
- Return user-friendly error messages
- Log technical details separately

## 🚀 Creating New Agent Tools

### Step 1: Define Argument Model

```python
# In argument_models.py
class NewToolArgs(BaseModel):
    """Arguments for new_tool function."""
    
    primary_field: str = Field(..., description="Main input")
    config_field: str | None = Field(
        default=None, 
        description="Optional configuration"
    )
```

### Step 2: Implement Business Logic

```python
# In tool_implementations.py
async def new_tool_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the new_tool function."""
    
    # Context validation
    service = get_required_service()
    user_id = get_current_user_id()
    
    if not service or not user_id:
        return "Error: Agent context not properly initialized"
    
    # Argument parsing
    try:
        parsed = NewToolArgs.model_validate_json(args)
    except ValueError as e:
        return f"Error: Invalid arguments: {e}"
    
    # Business logic
    try:
        result = await service.new_operation(
            parsed.primary_field,
            config=parsed.config_field
        )
        return f"Successfully processed: {result.summary}"
    except Exception as e:
        return f"Error processing request: {e}"
```

### Step 3: Register Tool Definition

```python
# In tool_definitions.py
def get_tool_definitions() -> Sequence[FunctionTool]:
    """Return tool definitions."""
    
    # ... existing tools ...
    
    new_tool = FunctionTool(
        name="new_tool",
        description="Performs new operation with specified parameters",
        params_json_schema=NewToolArgs.model_json_schema(),
        on_invoke_tool=new_tool_impl,
    )
    
    return [
        # ... existing tools ...
        new_tool,
    ]
```

### Step 4: Update System Instructions

```python
# In system_instructions.py
SYSTEM_INSTRUCTIONS = f"""
...existing instructions...

New Tool Operations:
- Use new_tool when user requests specific operation
- Validate input parameters and provide clear feedback
- Handle edge cases gracefully
...
"""
```

### Step 5: Update Context (if needed)

```python
# In tool_context.py (if new service needed)
_new_service: NewService | None = None

def set_agent_context(
    todo_service: TodoService,
    tag_service: TagService, 
    new_service: NewService,  # Add new service
    user_id: UUID
) -> None:
    """Inject services & user context."""
    global _todo_service, _tag_service, _new_service, _current_user_id
    _todo_service = todo_service
    _tag_service = tag_service
    _new_service = new_service
    _current_user_id = user_id

def get_new_service() -> NewService | None:
    """Get the new service instance."""
    return _new_service
```

## 🧪 Testing Patterns

### Unit Testing Tool Implementations

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_new_tool_impl():
    """Test new tool implementation."""
    
    # Arrange
    mock_service = AsyncMock()
    mock_service.new_operation.return_value = MockResult(summary="test")
    
    with patch('tool_context.get_required_service', return_value=mock_service), \
         patch('tool_context.get_current_user_id', return_value=uuid4()):
        
        # Act
        result = await new_tool_impl(
            None,  # ctx not used
            '{"primary_field": "test_value"}'
        )
        
        # Assert
        assert "Successfully processed: test" in result
        mock_service.new_operation.assert_called_once_with("test_value", config=None)
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_tool_integration():
    """Test tool integration with agent."""
    
    agent = get_todo_agent()
    tools = get_tool_definitions()
    
    # Verify tool registration
    assert len(tools) == expected_count
    assert any(tool.name == "new_tool" for tool in tools)
```

## 📊 Architecture Benefits

### Modularity
- Each file has single responsibility
- Easy to locate and modify specific functionality
- New tools don't affect existing ones

### Type Safety
- Pydantic models ensure data validation
- TypeScript-like development experience
- Runtime error prevention

### Testability
- Clean dependency injection via context
- Mockable service interfaces
- Isolated business logic testing

### Scalability
- Easy to add new tools following patterns
- Context management handles complexity
- Agent framework integration

### Maintainability
- Clear separation of concerns
- Consistent error handling patterns
- Self-documenting code structure

## 🔄 Future Extensions

### Multi-Domain Support

```
agents/
├── todo_agents/
│   └── tools/          # Current todo tools
├── calendar_agents/
│   └── tools/          # Calendar-specific tools
└── email_agents/
    └── tools/          # Email management tools
```

### Advanced Context Management

```python
# Enhanced context with request-scoped services
class AgentContext:
    def __init__(self, request_id: str, user_id: UUID):
        self.request_id = request_id
        self.user_id = user_id
        self.services: dict[str, Any] = {}
    
    def get_service(self, service_type: type[T]) -> T:
        return self.services[service_type.__name__]
```

### Tool Composition

```python
# Composite tools that use multiple services
async def complex_operation_impl(ctx: RunContextWrapper, args: str) -> str:
    """Combines multiple services for complex operations."""
    
    todo_service = get_todo_service()
    calendar_service = get_calendar_service()
    notification_service = get_notification_service()
    
    # Complex multi-service logic
    pass
```

### Plugin Architecture

```python
# Plugin-based tool loading
class ToolPlugin:
    def get_tool_definitions(self) -> Sequence[FunctionTool]:
        pass
    
    def register_context(self, context: AgentContext) -> None:
        pass
```

## 📈 Performance Considerations

### Lazy Loading
- Services loaded only when needed
- Context initialization per request
- Tool definitions cached

### Async Operations
- All implementations use async/await
- Non-blocking service calls
- Concurrent operation support

### Resource Management
- Context cleanup after requests
- Service connection pooling
- Memory-efficient argument parsing

## 🔐 Security Guidelines

### Data Privacy
- Never expose user UUIDs in responses
- Sanitize error messages
- Validate user ownership

### Input Validation
- Pydantic model validation
- SQL injection prevention
- Type coercion safety

### Access Control
- Context-based user validation
- Service-level authorization
- Tool execution permissions

This architecture provides a solid foundation for building scalable, maintainable AI agent tools while following best practices for modern Python development.
