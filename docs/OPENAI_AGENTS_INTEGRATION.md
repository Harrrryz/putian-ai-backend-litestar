# OpenAI Agents SDK Integration Guide

This guide explains how to use the new agent session models that provide persistent conversation history for the OpenAI Agents Python SDK.

## Overview

The integration adds two new database models and a custom session implementation:

- **`AgentSession`** - Stores agent conversation sessions (`src/app/db/models/agent_session.py`)
- **`SessionMessage`** - Stores individual messages within sessions (`src/app/db/models/session_message.py`)
- **`DatabaseSession`** - Custom session class that integrates with OpenAI Agents SDK (`src/app/lib/database_session.py`)

## Implementation Status

✅ **Complete** - All models and functionality implemented
- Database models created with proper relationships
- Migration `ff547aed8ea6` applied successfully
- Custom DatabaseSession class implementing OpenAI SDK Session protocol
- Comprehensive test suite available
- Full documentation with examples

## Database Models

### AgentSession Model

Stores metadata and configuration for agent conversation sessions.

**Fields:**
- `id` (UUID) - Primary key
- `session_id` (str) - User-defined session identifier (indexed)
- `session_name` (str, optional) - Human-readable session name
- `description` (str, optional) - Session description
- `is_active` (bool) - Whether the session is active (default: True)
- `user_id` (UUID) - Foreign key to user_account (with CASCADE delete)
- `agent_name` (str, optional) - Name of the agent
- `agent_instructions` (str, optional) - Agent instructions/prompt
- `created_at`, `updated_at` - Automatic timestamps

**Relationships:**
- `user` - Many-to-one with User model
- `messages` - One-to-many with SessionMessage model

### SessionMessage Model

Stores individual messages within agent conversations.

**Fields:**
- `id` (UUID) - Primary key
- `role` (MessageRole enum) - Message role: 'user', 'assistant', 'system', 'tool'
- `content` (str) - Message content
- `tool_call_id` (str, optional) - Tool call identifier
- `tool_name` (str, optional) - Tool name
- `extra_data` (str, optional) - Additional metadata as JSON string
- `session_id` (UUID) - Foreign key to agent_session (with CASCADE delete)
- `created_at`, `updated_at` - Automatic timestamps

**Relationships:**
- `session` - Many-to-one with AgentSession model

### MessageRole Enum

Defines the possible message roles compatible with OpenAI Agents SDK:
- `USER` = "user" - Messages from the user
- `ASSISTANT` = "assistant" - Messages from the AI agent
- `SYSTEM` = "system" - System prompts and instructions
- `TOOL` = "tool" - Tool call results and responses

**Location:** `src/app/db/models/session_message.py`

## File Structure

```
src/app/
├── db/models/
│   ├── agent_session.py      # AgentSession model
│   └── session_message.py    # SessionMessage model & MessageRole enum
└── lib/
    └── database_session.py   # DatabaseSession implementation

tests/unit/
└── test_agent_session_models.py  # Comprehensive test suite
```

## DatabaseSession Class

The `DatabaseSession` class implements the OpenAI Agents SDK Session protocol, providing persistent conversation history stored in the database.

**Location:** `src/app/lib/database_session.py`

### Basic Usage

```python
from app.lib.database_session import DatabaseSession

# Create a database session
session = DatabaseSession(
    session_id="conversation_123",
    user_id="user_uuid_here",
    db_session=async_db_session,  # SQLAlchemy AsyncSession
    agent_name="Assistant",
    agent_instructions="You are a helpful assistant.",
    session_name="Example Conversation",
)

# Use with OpenAI Agents SDK
from agents import Agent, Runner

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
)

result = await Runner.run(
    agent,
    "Hello, how are you?",
    session=session
)
```

### Session Operations

The `DatabaseSession` class provides all required Session protocol methods:

#### get_items(limit=None)
Retrieve conversation history for the session.

```python
# Get all messages
messages = await session.get_items()

# Get last 10 messages
recent_messages = await session.get_items(limit=10)

# Messages are returned in OpenAI format:
# [
#     {"role": "user", "content": "Hello"},
#     {"role": "assistant", "content": "Hi there!"}
# ]
```

#### add_items(items)
Store new messages in the session.

```python
await session.add_items([
    {"role": "user", "content": "What's the weather?"},
    {"role": "assistant", "content": "I'll help you check the weather."}
])
```

#### pop_item()
Remove and return the most recent message.

```python
last_message = await session.pop_item()
# Returns: {"role": "assistant", "content": "..."}
```

#### clear_session()
Clear all messages from the session.

```python
await session.clear_session()
```

#### update_session_metadata()
Update session metadata.

```python
await session.update_session_metadata(
    session_name="Updated Session Name",
    agent_name="New Agent Name",
    is_active=False
)
```

## Integration with Litestar

### Service Class

Create a service class for managing agent sessions:

```python
from app.lib.database_session import DatabaseSession

class AgentSessionService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    def create_session(
        self,
        session_id: str,
        user_id: str,
        agent_name: str | None = None,
        agent_instructions: str | None = None,
        session_name: str | None = None,
    ) -> DatabaseSession:
        return DatabaseSession(
            session_id=session_id,
            user_id=user_id,
            db_session=self.db_session,
            agent_name=agent_name,
            agent_instructions=agent_instructions,
            session_name=session_name,
        )
    
    async def list_user_sessions(self, user_id: str) -> list[dict]:
        """List all sessions for a user."""
        from sqlalchemy.future import select
        from app.db.models import AgentSession
        
        stmt = select(AgentSession).where(AgentSession.user_id == user_id)
        result = await self.db_session.execute(stmt)
        sessions = result.scalars().all()
        
        return [
            {
                "id": str(session.id),
                "session_id": session.session_id,
                "session_name": session.session_name,
                "agent_name": session.agent_name,
                "is_active": session.is_active,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
            for session in sessions
        ]
```

### Controller Example

```python
from litestar import Controller, post, get
from litestar.di import Provide

class AgentController(Controller):
    path = "/agents"
    
    @post("/sessions/{session_id}/chat")
    async def chat_with_agent(
        self,
        session_id: str,
        user_id: str,  # From JWT token or session
        message: str,
        agent_service: AgentSessionService = Provide(AgentSessionService),
    ) -> dict:
        # Create or get existing session
        session = agent_service.create_session(
            session_id=session_id,
            user_id=user_id,
            agent_name="Assistant",
            agent_instructions="You are a helpful assistant.",
        )
        
        # Use with OpenAI Agents SDK
        from agents import Agent, Runner
        
        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
        )
        
        result = await Runner.run(agent, message, session=session)
        
        return {
            "response": result.final_output,
            "session_id": session_id,
        }
    
    @get("/sessions")
    async def list_sessions(
        self,
        user_id: str,
        agent_service: AgentSessionService = Provide(AgentSessionService),
    ) -> list[dict]:
        return await agent_service.list_user_sessions(user_id)
```

## Message Format

The system automatically converts between OpenAI Agents SDK format and database storage:

### OpenAI Format (what the SDK expects/returns)
```python
{
    "role": "user",
    "content": "Hello, world!",
    "tool_call_id": "call_123",  # Optional
    "tool_name": "calculator",   # Optional
    # Any additional metadata...
}
```

### Database Storage
- `role` → `MessageRole` enum
- `content` → `content` field
- `tool_call_id` → `tool_call_id` field
- `tool_name` → `tool_name` field
- Additional metadata → `extra_data` field (JSON string)

## Advanced Features

### Tool Call Support

The system supports tool calls with metadata:

```python
await session.add_items([
    {"role": "user", "content": "Calculate 2 + 2"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "calculator",
                    "arguments": '{"operation": "add", "a": 2, "b": 2}'
                }
            }
        ]
    },
    {
        "role": "tool",
        "tool_call_id": "call_123",
        "name": "calculator",
        "content": "4"
    },
    {"role": "assistant", "content": "2 + 2 equals 4."}
])
```

### Session Management

```python
# Create multiple sessions for the same user
session_1 = DatabaseSession("session_1", user_id, db_session)
session_2 = DatabaseSession("session_2", user_id, db_session)

# Each session maintains independent conversation history
await session_1.add_items([{"role": "user", "content": "Hello from session 1"}])
await session_2.add_items([{"role": "user", "content": "Hello from session 2"}])
```

### Error Handling

```python
try:
    result = await Runner.run(agent, message, session=session)
except Exception as e:
    # Handle agent errors
    await session.add_items([
        {"role": "system", "content": f"Error occurred: {e}"}
    ])
```

## Best Practices

1. **Session IDs**: Use meaningful session IDs (e.g., "user123_todo_2024")
2. **User Isolation**: Always filter sessions by user_id for security
3. **Cleanup**: Consider implementing session cleanup for old/inactive sessions
4. **Error Handling**: Handle database errors gracefully
5. **Performance**: Use limits when retrieving conversation history for long sessions
6. **Security**: Validate user permissions before accessing sessions

## Example Use Cases

### Todo Assistant Integration

```python
# Create session for todo management
session = DatabaseSession(
    session_id=f"user_{user_id}_todo_assistant",
    user_id=user_id,
    db_session=db_session,
    agent_name="Todo Assistant",
    agent_instructions="You help users manage their todo items.",
    session_name="Todo Management Chat",
)

# Use existing todo agent
from app.domain.todo.todo_agents import TodoAgent

agent = TodoAgent()
result = await Runner.run(
    agent,
    "Create a todo item for grocery shopping tomorrow",
    session=session
)
```

### Multi-Agent Handoffs

```python
# Support agent session
support_session = DatabaseSession("support_123", user_id, db_session)

# Billing agent session (shared context)
billing_session = DatabaseSession("billing_123", user_id, db_session)

# Both agents can see conversation history
support_result = await Runner.run(support_agent, message, session=support_session)
billing_result = await Runner.run(billing_agent, message, session=billing_session)
```

## Migration Details

The models were added via migration `ff547aed8ea6` which was successfully applied. The migration creates:

1. **`agent_session` table** with proper indexes:
   - Primary key on `id` (UUID)
   - Index on `session_id` for fast lookups
   - Foreign key to `user_account` with CASCADE delete
   
2. **`session_message` table** with relationships:
   - Primary key on `id` (UUID) 
   - Foreign key to `agent_session` with CASCADE delete
   - Message role enum constraint
   
3. **Database constraints and features**:
   - Cascade delete relationships (deleting a session removes all messages)
   - Audit timestamps (created_at, updated_at)
   - UUID primary keys for all entities
   - Proper indexing for performance

**Migration command used:**
```bash
uv run app database make-migrations
uv run app database upgrade
```

No existing data is affected by this migration.

## Testing

A comprehensive test suite is available at `tests/unit/test_agent_session_models.py` covering:

- ✅ Model creation and validation
- ✅ Relationship functionality (User ↔ AgentSession ↔ SessionMessage)
- ✅ MessageRole enum operations
- ✅ Cascade delete behavior
- ✅ Database constraints and indexes

**Run tests with:**
```bash
uv run python -m pytest tests/unit/test_agent_session_models.py -v
```

## Conclusion

This integration provides a robust foundation for persistent agent conversations while maintaining compatibility with the OpenAI Agents SDK. The database-backed sessions ensure conversation history is preserved across application restarts and enable advanced features like session management and multi-user isolation.

**Key Benefits:**
- 🔒 **User Isolation** - Sessions are properly scoped to users with security
- 📝 **Persistent History** - Conversations survive application restarts  
- 🔧 **Tool Support** - Full support for tool calls and metadata
- 🚀 **Performance** - Optimized queries with proper indexing
- 🧪 **Tested** - Comprehensive test coverage for reliability
- 📚 **Documented** - Complete usage examples and best practices
