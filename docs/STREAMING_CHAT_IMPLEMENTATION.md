# Streaming Chat Implementation (SSE)

This document provides a comprehensive guide to the Server-Sent Events (SSE) implementation for real-time streaming chat functionality in the Todo Agents domain.

## Table of Contents

1. [Overview](#overview)
2. [SSE Architecture](#sse-architecture)
3. [Streaming Workflow](#streaming-workflow)
4. [Event Types and Structure](#event-types-and-structure)
5. [Implementation Details](#implementation-details)
6. [Client Integration](#client-integration)
7. [Error Handling](#error-handling)
8. [Performance Optimization](#performance-optimization)
9. [Security Considerations](#security-considerations)
10. [Testing SSE Endpoints](#testing-sse-endpoints)

## Overview

The streaming chat implementation uses Server-Sent Events (SSE) to provide real-time, bidirectional communication between clients and the AI-powered todo agent. This enables users to receive instant feedback as the AI processes their requests, creates todos, and manages their schedules.

### Key Features

- **Real-time streaming**: Instant response delivery as the AI processes requests
- **Event-driven architecture**: Structured event types for different stages of processing
- **Session persistence**: Conversation history maintained across requests
- **Error resilience**: Comprehensive error handling and recovery
- **Rate limiting**: Built-in quota management and usage tracking
- **Connection management**: Proper cleanup and resource management

## SSE Architecture

### Core Components

```
Client → Litestar Controller → TodoAgentService → OpenAI Agents SDK → AI Model
  ↓         ↓                    ↓                  ↓              ↓
SSE ← ServerSentEvent ← Event Stream ← Runner.run_streamed ← Response
```

### Architecture Layers

1. **Controller Layer** (`TodoAgentController`)
   - Handles HTTP requests and SSE responses
   - Manages request validation and authentication
   - Coordinates with service layer

2. **Service Layer** (`TodoAgentService`)
   - Implements streaming business logic
   - Manages AI agent interactions
   - Handles session persistence

3. **Agent Layer** (OpenAI Agents SDK)
   - Provides streaming capabilities
   - Manages conversation context
   - Executes AI model interactions

4. **SSE Transport Layer** (Litestar)
   - Formats events for SSE protocol
   - Manages connection lifecycle
   - Handles content encoding

## Streaming Workflow

### 1. Client Request Flow

```python
# Client initiates streaming request
POST /api/todos/agent-create/stream
{
    "messages": [
        {"role": "user", "content": "Create a todo for meeting tomorrow"}
    ],
    "session_id": "user_123_session_abc"
}
```

### 2. Server Processing Flow

```python
async def agent_create_todo_stream(
    self,
    current_user: m.User,
    data: AgentTodoRequest,
    todo_agent_service: TodoAgentService,
) -> ServerSentEvent:
    """Stream todo agent responses as Server-Sent Events."""

    # Extract user message from conversation history
    user_message = extract_user_message(data.messages)

    # Create event stream generator
    async def event_stream():
        async for payload in todo_agent_service.stream_chat_with_agent(
            user_id=str(current_user.id),
            message=user_message,
            session_id=data.session_id,
        ):
            yield ServerSentEventMessage(
                event=payload.get("event", "message"),
                data=serialize_payload(payload.get("data"))
            )

    return ServerSentEvent(event_stream())
```

### 3. Agent Processing Flow

```python
async def stream_chat_with_agent(
    self,
    user_id: str,
    message: str,
    session_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream agent responses as structured events."""

    # Initialize session
    yield {"event": "session_initialized", "data": {"session_id": session_id}}

    # Set up agent context
    set_agent_context(self.todo_service, self.tag_service, UUID(user_id))

    # Create streaming runner
    stream = Runner.run_streamed(
        agent=get_todo_agent(),
        input=message,
        session=session,
        max_turns=20,
    )

    # Process streaming events
    async for event in stream.stream_events():
        payloads = self._dispatch_stream_event(event)
        for payload in payloads:
            yield payload

    # Send completion and history
    yield {"event": "completed", "data": {"final_message": final_message}}
    yield {"event": "history", "data": await self.get_session_history(session_id)}
```

## Event Types and Structure

### Core Event Types

#### 1. Session Events

```javascript
// Session initialization
event: session_initialized
data: {
    "session_id": "user_123_session_abc"
}
```

#### 2. Message Events

```javascript
// Real-time message deltas
event: message_delta
data: {
    "content": "I'll create a todo for your meeting"
}

// Complete message
event: message
data: {
    "content": "I've created a todo for your meeting tomorrow at 2 PM"
}
```

#### 3. Tool Execution Events

```javascript
// Tool call initiated
event: tool_call
data: {
    "tool_name": "create_todo",
    "arguments": {
        "item": "Team meeting",
        "start_time": "2024-01-15 14:00:00",
        "importance": "high"
    }
}

// Tool execution result
event: tool_result
data: {
    "output": {
        "todo_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "created",
        "item": "Team meeting"
    }
}
```

#### 4. Status Events

```javascript
// Agent updates
event: agent_updated
data: {
    "name": "TodoAgent"
}

// Stream completion
event: completed
data: {
    "final_message": "Your todo has been created successfully"
}

// Conversation history
event: history
data: [
    {
        "role": "user",
        "content": "Create a todo for meeting tomorrow"
    },
    {
        "role": "assistant",
        "content": "I've created a todo for your meeting tomorrow"
    }
]
```

#### 5. Error Events

```javascript
// General errors
event: error
data: {
    "status": "error",
    "message": "Failed to process request: Invalid date format"
}

// Rate limiting
event: rate_limit_exceeded
data: {
    "message": "Monthly quota exceeded",
    "current_usage": 201,
    "monthly_limit": 200,
    "remaining_quota": 0,
    "reset_date": "2024-02-01T00:00:00Z"
}
```

## Implementation Details

### Event Serialization

```python
def _serialize_payload(payload: Any) -> str:
    """Serialize event payload for SSE transmission."""
    if isinstance(payload, bytes):
        return payload.decode()
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, default=str)
```

### Event Dispatching

The service uses a sophisticated event dispatching system to handle different types of streaming events:

```python
def _dispatch_stream_event(
    self,
    event: Any,
    last_message_chunks: list[str],
) -> tuple[bool, list[dict[str, Any]], str | None]:
    """Dispatch streaming events to appropriate handlers."""

    # Handle text deltas
    if handled := self._handle_raw_response_event(event, last_message_chunks):
        return handled

    # Handle agent updates
    if event.type == "agent_updated_stream_event":
        return self._handle_agent_update(event)

    # Handle tool execution
    if event.type == "run_item_stream_event":
        return self._handle_run_item_stream_event(event)

    return False, [], None
```

### Session Management

```python
class TodoAgentService:
    def __init__(self, session_db_path: str = "conversations.db"):
        self.session_db_path = session_db_path
        self._sessions: dict[str, SQLiteSession] = {}

    async def stream_chat_with_agent(self, user_id: str, message: str, session_id: str):
        # Get or create session
        if session_id not in self._sessions:
            self._sessions[session_id] = SQLiteSession(session_id, self.session_db_path)

        session = self._sessions[session_id]

        # Session automatically persists conversation history
        stream = Runner.run_streamed(agent, message, session=session)
        async for event in stream.stream_events():
            # Process events...
            pass
```

## Client Integration

### JavaScript Client Example

```javascript
class StreamingTodoClient {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.authToken = authToken;
        this.eventSource = null;
    }

    async streamTodoCreation(messages, sessionId, onEvent) {
        const response = await fetch(`${this.baseUrl}/api/todos/agent-create/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.authToken}`,
            },
            body: JSON.stringify({
                messages: messages,
                session_id: sessionId
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const events = this.parseSSEChunk(chunk);

                for (const event of events) {
                    onEvent(event);
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    parseSSEChunk(chunk) {
        const events = [];
        const lines = chunk.split('\n');
        let currentEvent = {};

        for (const line of lines) {
            if (line.startsWith('event:')) {
                currentEvent.type = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
                currentEvent.data = JSON.parse(line.slice(5).trim());
            } else if (line === '') {
                if (currentEvent.type) {
                    events.push(currentEvent);
                    currentEvent = {};
                }
            }
        }

        return events;
    }
}

// Usage example
const client = new StreamingTodoClient('https://api.example.com', 'token');

client.streamTodoCreation(
    [{role: 'user', content: 'Schedule team meeting for tomorrow'}],
    'user_123_session',
    (event) => {
        switch(event.type) {
            case 'message_delta':
                console.log('Streaming:', event.data.content);
                break;
            case 'tool_call':
                console.log('Executing tool:', event.data.tool_name);
                break;
            case 'completed':
                console.log('Complete:', event.data.final_message);
                break;
            case 'error':
                console.error('Error:', event.data.message);
                break;
        }
    }
);
```

### React Integration Example

```jsx
import React, { useState, useEffect, useRef } from 'react';

function StreamingTodoAgent() {
    const [messages, setMessages] = useState([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [currentResponse, setCurrentResponse] = useState('');
    const abortControllerRef = useRef(null);

    const streamResponse = async (userMessage) => {
        setIsStreaming(true);
        setCurrentResponse('');

        try {
            abortControllerRef.current = new AbortController();

            const response = await fetch('/api/todos/agent-create/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: [{ role: 'user', content: userMessage }],
                    session_id: 'default_session'
                }),
                signal: abortControllerRef.current.signal
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            switch (data.event) {
                                case 'message_delta':
                                    setCurrentResponse(prev => prev + data.data.content);
                                    break;
                                case 'completed':
                                    setMessages(prev => [...prev, {
                                        role: 'assistant',
                                        content: data.data.final_message
                                    }]);
                                    break;
                                case 'error':
                                    console.error('Stream error:', data.data);
                                    break;
                            }
                        } catch (e) {
                            // Ignore malformed JSON
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Streaming error:', error);
            }
        } finally {
            setIsStreaming(false);
            setCurrentResponse('');
        }
    };

    const stopStreaming = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    };

    return (
        <div>
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.role}`}>
                        {msg.content}
                    </div>
                ))}
                {isStreaming && currentResponse && (
                    <div className="message assistant streaming">
                        {currentResponse}
                    </div>
                )}
            </div>

            <div className="controls">
                <button
                    onClick={() => streamResponse('Create a todo for tomorrow')}
                    disabled={isStreaming}
                >
                    {isStreaming ? 'Streaming...' : 'Send Message'}
                </button>
                {isStreaming && (
                    <button onClick={stopStreaming}>Stop</button>
                )}
            </div>
        </div>
    );
}
```

## Error Handling

### Server-Side Error Handling

```python
async def event_stream():
    try:
        # Validate input
        if not data.messages:
            yield ServerSentEventMessage(
                event="error",
                data={"status": "error", "message": "No messages provided"}
            )
            return

        # Process streaming
        async for payload in todo_agent_service.stream_chat_with_agent(...):
            yield ServerSentEventMessage(
                event=payload.get("event", "message"),
                data=serialize_payload(payload.get("data"))
            )

    except RateLimitExceededException as exc:
        yield ServerSentEventMessage(
            event="rate_limit_exceeded",
            data={
                "message": exc.detail,
                "current_usage": exc.current_usage,
                "monthly_limit": exc.monthly_limit,
                "remaining_quota": max(0, exc.monthly_limit - exc.current_usage)
            }
        )
    except Exception as exc:
        logger.exception("Agent streaming failed", error=exc)
        yield ServerSentEventMessage(
            event="error",
            data={"status": "error", "message": f"Streaming failed: {exc}"}
        )
```

### Client-Side Error Handling

```javascript
async function streamWithRetry(client, messages, maxRetries = 3) {
    let lastError;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            await client.streamTodoCreation(messages, 'default_session', handleEvent);
            return; // Success, exit retry loop
        } catch (error) {
            lastError = error;

            if (error.type === 'rate_limit_exceeded') {
                // Wait for quota reset
                const resetTime = new Date(error.data.reset_date);
                const waitTime = resetTime - Date.now();
                if (waitTime > 0) {
                    await new Promise(resolve => setTimeout(resolve, waitTime));
                    continue; // Retry after quota reset
                }
            }

            if (attempt < maxRetries - 1) {
                // Exponential backoff
                const delay = Math.pow(2, attempt) * 1000;
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    throw lastError; // All retries exhausted
}
```

## Performance Optimization

### Connection Pooling

```python
class TodoAgentService:
    def __init__(self, max_sessions: int = 1000):
        self.max_sessions = max_sessions
        self._sessions = {}
        self._session_access = {}

    def _cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove inactive sessions to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        inactive_sessions = [
            session_id for session_id, last_access in self._session_access.items()
            if last_access < cutoff_time
        ]

        for session_id in inactive_sessions:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._session_access:
                del self._session_access[session_id]
```

### Streaming Optimization

```python
async def stream_chat_with_agent(self, ...):
    """Optimized streaming with buffering and compression."""

    # Use buffering for small events
    event_buffer = []
    buffer_size = 0
    max_buffer_size = 1024  # 1KB

    async for event in self._generate_events(...):
        event_json = json.dumps(event)
        event_size = len(event_json.encode('utf-8'))

        # Buffer small events
        if buffer_size + event_size < max_buffer_size:
            event_buffer.append(event)
            buffer_size += event_size
            continue

        # Flush buffer
        if event_buffer:
            yield {"event": "batch", "data": event_buffer}
            event_buffer = []
            buffer_size = 0

        # Send large events immediately
        yield event

    # Flush remaining events
    if event_buffer:
        yield {"event": "batch", "data": event_buffer}
```

### Client-Side Optimization

```javascript
class OptimizedStreamingClient {
    constructor(options = {}) {
        this.batchSize = options.batchSize || 10;
        this.batchTimeout = options.batchTimeout || 100; // ms
        this.eventBuffer = [];
        this.batchTimer = null;
    }

    handleEvent(event) {
        this.eventBuffer.push(event);

        // Flush buffer when full or timeout
        if (this.eventBuffer.length >= this.batchSize) {
            this.flushBuffer();
        } else if (!this.batchTimer) {
            this.batchTimer = setTimeout(() => {
                this.flushBuffer();
            }, this.batchTimeout);
        }
    }

    flushBuffer() {
        if (this.batchTimer) {
            clearTimeout(this.batchTimer);
            this.batchTimer = null;
        }

        if (this.eventBuffer.length > 0) {
            this.processBatch(this.eventBuffer);
            this.eventBuffer = [];
        }
    }

    processBatch(events) {
        // Process multiple events efficiently
        const messageDeltas = events
            .filter(e => e.type === 'message_delta')
            .map(e => e.data.content)
            .join('');

        if (messageDeltas) {
            this.updateMessage(messageDeltas);
        }

        // Handle other event types
        events
            .filter(e => e.type !== 'message_delta')
            .forEach(event => this.handleSingleEvent(event));
    }
}
```

## Security Considerations

### Authentication and Authorization

```python
@post(path="/agent-create/stream", operation_id="agent_create_todo_stream")
async def agent_create_todo_stream(
    self,
    current_user: m.User,  # JWT authentication required
    data: AgentTodoRequest,
    todo_agent_service: TodoAgentService,
) -> ServerSentEvent:
    """Stream todo agent responses with authentication."""

    # User is already authenticated via Litestar's JWT middleware
    # Additional authorization checks can be added here

    async def event_stream():
        # Verify user has access to requested session
        if data.session_id and not data.session_id.startswith(f"user_{current_user.id}_"):
            yield ServerSentEventMessage(
                event="error",
                data={"message": "Access denied: Invalid session"}
            )
            return

        # Continue with streaming...
```

### Input Validation and Sanitization

```python
def _validate_stream_request(self, data: AgentTodoRequest, user_id: str) -> None:
    """Validate streaming request for security."""

    # Check message count limits
    if len(data.messages) > 50:
        raise ValueError("Too many messages in conversation")

    # Validate message content
    for message in data.messages:
        if not isinstance(message.get('content'), str):
            raise ValueError("Invalid message content")

        if len(message['content']) > 10000:  # 10KB limit
            raise ValueError("Message content too long")

    # Validate session ID format
    if data.session_id and not re.match(r'^[a-zA-Z0-9_-]+$', data.session_id):
        raise ValueError("Invalid session ID format")
```

### Rate Limiting

```python
class StreamingRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.window_size = 60  # 1 minute
        self.max_requests = 10  # requests per minute

    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded streaming rate limit."""
        key = f"stream_rate_limit:{user_id}"
        current_time = int(time.time())

        # Use sliding window counter
        async with self.redis.pipeline() as pipe:
            pipe.zremrangebyscore(key, 0, current_time - self.window_size)
            pipe.zcard(key)
            pipe.expire(key, self.window_size)

            _, request_count, _ = await pipe.execute()

        return request_count < self.max_requests

    async def record_request(self, user_id: str) -> None:
        """Record a streaming request."""
        key = f"stream_rate_limit:{user_id}"
        current_time = int(time.time())
        await self.redis.zadd(key, {str(current_time): current_time})
```

### Content Security

```python
def _sanitize_tool_output(self, tool_output: Any) -> Any:
    """Sanitize tool output for streaming."""

    if isinstance(tool_output, dict):
        # Remove sensitive fields
        sensitive_fields = ['password', 'token', 'api_key', 'secret']
        sanitized = {}

        for key, value in tool_output.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = self._sanitize_tool_output(value)

        return sanitized

    elif isinstance(tool_output, list):
        return [self._sanitize_tool_output(item) for item in tool_output]

    elif isinstance(tool_output, str):
        # Limit string length to prevent huge responses
        if len(tool_output) > 5000:
            return tool_output[:5000] + '... [truncated]'
        return tool_output

    return tool_output
```

## Testing SSE Endpoints

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock

class StubTodoAgentService:
    """Mock service for testing streaming endpoints."""

    async def stream_chat_with_agent(
        self,
        *,
        user_id: str,
        message: str,
        session_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"event": "session_initialized", "data": {"session_id": session_id}}
        yield {"event": "message", "data": {"content": "Working on it"}}
        yield {"event": "completed", "data": {"final_message": "Done"}}
        yield {"event": "history", "data": []}

@pytest.mark.anyio
async def test_agent_create_todo_stream_success():
    """Test successful streaming response."""
    controller = TodoAgentController()
    service = StubTodoAgentService()
    user = SimpleNamespace(id=123)

    request = AgentTodoRequest(
        messages=[{"role": "user", "content": "Create a todo"}],
        session_id="test_session"
    )

    response = await controller.agent_create_todo_stream(
        current_user=user,
        data=request,
        todo_agent_service=service,
    )

    # Collect all SSE events
    events = []
    async for chunk in response.iterator:
        events.append(chunk.decode())

    # Verify events
    assert any("event: session_initialized" in event for event in events)
    assert any("event: completed" in event for event in events)
    assert any("Done" in event for event in events)
```

### Integration Tests

```python
@pytest.mark.anyio
async def test_streaming_end_to_end(client, auth_headers):
    """Test complete streaming workflow."""

    # Start streaming request
    response = await client.post(
        "/api/todos/agent-create/stream",
        json={
            "messages": [{"role": "user", "content": "Create test todo"}],
            "session_id": "integration_test"
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Collect events
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            try:
                event_data = json.loads(line[6:])
                events.append(event_data)
            except json.JSONDecodeError:
                continue

    # Verify event sequence
    event_types = [event.get("event") for event in events]
    assert "session_initialized" in event_types
    assert "completed" in event_types
    assert "history" in event_types
```

### Client Testing

```javascript
describe('Streaming Todo Client', () => {
    let client;
    let mockFetch;

    beforeEach(() => {
        mockFetch = jest.fn();
        global.fetch = mockFetch;
        client = new StreamingTodoClient('http://localhost:8000', 'test-token');
    });

    test('handles streaming response correctly', async () => {
        const mockEvents = [
            'event: session_initialized\ndata: {"session_id":"test"}\n\n',
            'event: message_delta\ndata: {"content":"Hello "}\n\n',
            'event: message_delta\ndata: {"content":"world"}\n\n',
            'event: completed\ndata: {"final_message":"Hello world"}\n\n'
        ];

        const mockResponse = {
            body: {
                getReader: () => ({
                    read: jest.fn()
                        .mockResolvedValueOnce({
                            done: false,
                            value: new TextEncoder().encode(mockEvents[0])
                        })
                        .mockResolvedValueOnce({
                            done: false,
                            value: new TextEncoder().encode(mockEvents[1])
                        })
                        .mockResolvedValueOnce({
                            done: false,
                            value: new TextEncoder().encode(mockEvents[2])
                        })
                        .mockResolvedValueOnce({
                            done: false,
                            value: new TextEncoder().encode(mockEvents[3])
                        })
                        .mockResolvedValueOnce({ done: true })
                })
            }
        };

        mockFetch.mockResolvedValue(mockResponse);

        const events = [];
        await client.streamTodoCreation(
            [{role: 'user', content: 'test'}],
            'test_session',
            (event) => events.push(event)
        );

        expect(events).toHaveLength(4);
        expect(events[0].type).toBe('session_initialized');
        expect(events[1].data.content).toBe('Hello ');
        expect(events[2].data.content).toBe('world');
        expect(events[3].data.final_message).toBe('Hello world');
    });
});
```

## Conclusion

The Streaming Chat Implementation provides a robust, scalable foundation for real-time AI-powered todo management. By leveraging Server-Sent Events, the system delivers immediate feedback and maintains conversation context while ensuring security, performance, and reliability.

The implementation follows best practices for:

- **Real-time communication**: Efficient event streaming with proper serialization
- **Error handling**: Comprehensive error management and recovery mechanisms
- **Security**: Authentication, authorization, and input validation
- **Performance**: Connection management, buffering, and resource optimization
- **Testing**: Complete test coverage for unit and integration scenarios

This architecture enables seamless integration with modern web applications while maintaining the scalability required for production deployments.