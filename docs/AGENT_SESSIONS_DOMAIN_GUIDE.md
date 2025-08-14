# Agent Sessions Domain

The Agent Sessions domain provides functionality for managing AI agent conversation sessions and their messages. This domain enables persistent chat sessions with AI agents, storing conversation history and session metadata.

## Overview

The domain consists of two main entities:

1. **AgentSession**: Represents a conversation session with an AI agent
2. **SessionMessage**: Represents individual messages within a session

## Features

### Agent Session Management
- Create, read, update, and delete agent sessions
- Activate/deactivate sessions
- Session metadata (name, description, agent configuration)
- User ownership and access control

### Message Management
- Store conversation messages with roles (user, assistant, system, tool)
- Message metadata (tool calls, extra data)
- Clear session messages
- Retrieve conversation history

### Conversation API
- Simple conversation endpoint for AI agent interactions
- Automatic session creation and message persistence
- Mock response system (ready for OpenAI Agents SDK integration)

## API Endpoints

### Agent Sessions

#### List Sessions
```http
GET /api/agent-sessions
```
Lists all agent sessions for the authenticated user with pagination and filtering.

#### Create Session
```http
POST /api/agent-sessions
Content-Type: application/json

{
  "session_id": "my-session-001",
  "session_name": "Project Planning Chat",
  "description": "AI assistant for project planning tasks",
  "agent_name": "Planning Assistant",
  "agent_instructions": "You are a helpful project planning assistant.",
  "is_active": true
}
```

#### Get Session
```http
GET /api/agent-sessions/{session_id}
```

#### Update Session
```http
PATCH /api/agent-sessions/{session_id}
Content-Type: application/json

{
  "session_name": "Updated Session Name",
  "description": "Updated description"
}
```

#### Delete Session
```http
DELETE /api/agent-sessions/{session_id}
```

#### Activate/Deactivate Session
```http
PUT /api/agent-sessions/{session_id}/activate
PUT /api/agent-sessions/{session_id}/deactivate
```

### Session Messages

#### List Messages
```http
GET /api/agent-sessions/{session_id}/messages
```

#### Create Message
```http
POST /api/agent-sessions/{session_id}/messages
Content-Type: application/json

{
  "role": "user",
  "content": "Hello, how can you help me?",
  "tool_call_id": null,
  "tool_name": null,
  "extra_data": null
}
```

#### Get Message
```http
GET /api/agent-sessions/{session_id}/messages/{message_id}
```

#### Update Message
```http
PATCH /api/agent-sessions/{session_id}/messages/{message_id}
Content-Type: application/json

{
  "content": "Updated message content",
  "extra_data": "{\"edited\": true}"
}
```

#### Delete Message
```http
DELETE /api/agent-sessions/{session_id}/messages/{message_id}
```

#### Clear All Messages
```http
DELETE /api/agent-sessions/{session_id}/clear-messages
```

### Conversation API

#### Start/Continue Conversation
```http
POST /api/agent-sessions/conversation
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Hello, I need help with project planning"
    }
  ],
  "session_id": "my-session-001",
  "session_name": "Project Planning Chat",
  "agent_name": "Planning Assistant",
  "agent_instructions": "You are a helpful project planning assistant."
}
```

Response:
```json
{
  "session_id": "my-session-001",
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "response": "This is a mock response to: Hello, I need help with project planning",
  "messages_count": 2,
  "session_active": true
}
```

## Database Models

### AgentSession
- `id`: UUID (Primary Key)
- `session_id`: String (Unique per user)
- `session_name`: String (Optional)
- `description`: Text (Optional)
- `is_active`: Boolean
- `user_id`: UUID (Foreign Key to User)
- `agent_name`: String (Optional)
- `agent_instructions`: Text (Optional)
- `created_at`: DateTime
- `updated_at`: DateTime

### SessionMessage
- `id`: UUID (Primary Key)
- `role`: Enum (user, assistant, system, tool)
- `content`: Text
- `tool_call_id`: String (Optional)
- `tool_name`: String (Optional)
- `extra_data`: Text (Optional JSON)
- `session_id`: UUID (Foreign Key to AgentSession)
- `created_at`: DateTime
- `updated_at`: DateTime

## Services

### AgentSessionService
- Standard CRUD operations
- User-specific session retrieval
- Session activation/deactivation
- Session lookup by session_id

### SessionMessageService
- Standard CRUD operations
- Session-specific message retrieval
- Message counting
- Bulk message clearing
- Recent message retrieval

## Usage Examples

### Python Client Example
```python
import httpx

# Create a session
session_data = {
    "session_id": "example-session",
    "session_name": "Example Chat",
    "agent_name": "Helper Bot"
}

async with httpx.AsyncClient() as client:
    # Create session
    response = await client.post(
        "http://localhost:8000/api/agent-sessions",
        json=session_data,
        headers={"Authorization": "Bearer your-jwt-token"}
    )
    session = response.json()
    
    # Start conversation
    conversation_data = {
        "messages": [{"role": "user", "content": "Hello!"}],
        "session_id": "example-session"
    }
    
    response = await client.post(
        "http://localhost:8000/api/agent-sessions/conversation",
        json=conversation_data,
        headers={"Authorization": "Bearer your-jwt-token"}
    )
    result = response.json()
    print(f"Agent response: {result['response']}")
```

### JavaScript/TypeScript Example
```typescript
interface ConversationRequest {
  messages: Array<{role: string; content: string}>;
  session_id?: string;
  session_name?: string;
  agent_name?: string;
  agent_instructions?: string;
}

interface ConversationResponse {
  session_id: string;
  session_uuid: string;
  response: string;
  messages_count: number;
  session_active: boolean;
}

async function startConversation(
  message: string,
  sessionId?: string
): Promise<ConversationResponse> {
  const response = await fetch('/api/agent-sessions/conversation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      messages: [{role: 'user', content: message}],
      session_id: sessionId,
      session_name: 'Chat Session'
    })
  });
  
  return response.json();
}
```

## Integration with OpenAI Agents SDK

The conversation endpoint is designed to be extended with the OpenAI Agents SDK. The current implementation provides a mock response, but can be easily replaced with actual agent logic:

```python
# In the conversation endpoint, replace the mock response with:
from app.domain.todo.todo_agents import create_todo_agent_session

# Create agent session with database persistence
agent_session = create_todo_agent_session(
    session_id=session.session_id,
    user_id=str(current_user.id),
    db_session=db_session,  # SQLAlchemy session
    todo_service=todo_service,
    tag_service=tag_service,
    session_name=session.session_name
)

# Run the agent with the user messages
response = await agent_session.run(data.messages)
```

## Security

- All endpoints require authentication
- Users can only access their own sessions and messages
- Session ownership is verified on all operations
- Proper error handling for unauthorized access

## Testing

The domain includes comprehensive test coverage:
- Unit tests for services
- Integration tests for controllers
- API endpoint testing
- Error case validation

To run tests:
```bash
pytest tests/unit/domain/agent_sessions/
pytest tests/integration/test_agent_sessions.py
```
