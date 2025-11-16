# Agent Testing & Development

This guide covers comprehensive testing strategies and development practices for AI agents in the todo application, including SimpleEnvironment usage, mock integration, performance testing, and debugging strategies.

## Table of Contents

1. [SimpleEnvironment for Testing AI Agents](#simpleenvironment-for-testing-ai-agents)
2. [Agent Tool Validation and Testing Strategies](#agent-tool-validation-and-testing-strategies)
3. [Mock AI Model Integration for Testing](#mock-ai-model-integration-for-testing)
4. [Test Fixture Setup and Isolation Patterns](#test-fixture-setup-and-isolation-patterns)
5. [Integration Testing for Agent Workflows](#integration-testing-for-agent-workflows)
6. [Performance Testing and Benchmarking](#performance-testing-and-benchmarking)
7. [Error Scenario Testing and Validation](#error-scenario-testing-and-validation)
8. [Test Data Management and Fixtures](#test-data-management-and-fixtures)
9. [Continuous Testing Strategies](#continuous-testing-strategies)
10. [Debug and Logging Strategies for Agents](#debug-and-logging-strategies-for-agents)

## SimpleEnvironment for Testing AI Agents

The `SimpleEnvironment` class provides a minimal testing environment for AI agents, implementing the ACE (Agent Capability Enhancement) framework's `TaskEnvironment` interface.

### Basic Implementation

```python
# agent-training.py
from ace import EnvironmentResult, TaskEnvironment, Sample

class SimpleEnvironment(TaskEnvironment):
    """Minimal environment for testing AI agents."""

    def evaluate(self, sample, generator_output):
        """Evaluate agent output against ground truth."""
        correct = sample.ground_truth.lower() in generator_output.final_answer.lower()
        return EnvironmentResult(
            feedback="Correct!" if correct else "Incorrect",
            ground_truth=sample.ground_truth,
        )
```

### Using SimpleEnvironment in Tests

```python
import pytest
from ace import Curator, Generator, OfflineAdapter, Playbook, Reflector
from agents.extensions.models.litellm_model import LitellmModel

@pytest.fixture
def simple_environment():
    """Create a simple environment for testing."""
    return SimpleEnvironment()

@pytest.fixture
def test_samples():
    """Create test samples for agent evaluation."""
    return [
        Sample(question="Create a todo for meeting", ground_truth="todo created"),
        Sample(question="What are my todos?", ground_truth="todo list"),
        Sample(question="Delete todo with ID 123", ground_truth="todo deleted"),
    ]

@pytest.mark.asyncio
async def test_agent_with_simple_environment(simple_environment, test_samples):
    """Test agent performance with SimpleEnvironment."""
    # Create mock model for testing
    model = LitellmModel(
        model="openai/glm-4.5",
        api_key="test-key",
        base_url="http://test-url",
    )

    # Create adapter with ACE components
    adapter = OfflineAdapter(
        playbook=Playbook(),
        generator=Generator(model),
        reflector=Reflector(model),
        curator=Curator(model),
    )

    # Run adaptation
    results = adapter.run(test_samples, simple_environment, epochs=1)

    # Verify results
    assert len(results) == len(test_samples)
    assert len(adapter.playbook.bullets()) > 0

    # Verify learned strategies
    strategies = adapter.playbook.bullets()
    assert any("create" in strategy.content.lower() for strategy in strategies)
```

### Custom Environment Implementations

```python
class TodoEnvironment(TaskEnvironment):
    """Custom environment for todo-specific testing."""

    def __init__(self, todo_service):
        self.todo_service = todo_service
        self.test_results = []

    def evaluate(self, sample, generator_output):
        """Evaluate agent actions against todo service state."""
        # Extract expected action from sample
        expected_action = sample.metadata.get("expected_action")
        todo_id = sample.metadata.get("todo_id")

        # Verify actual state in todo service
        if expected_action == "create":
            todos = await self.todo_service.list_todos(sample.user_id)
            actual_result = len(todos) > 0
        elif expected_action == "delete":
            try:
                await self.todo_service.get_todo(todo_id)
                actual_result = False  # Todo still exists
            except NotFoundError:
                actual_result = True   # Todo successfully deleted
        else:
            actual_result = False

        result = EnvironmentResult(
            feedback=f"{'✓' if actual_result else '✗'} {expected_action} operation",
            ground_truth=expected_action,
            score=1.0 if actual_result else 0.0,
        )

        self.test_results.append(result)
        return result
```

## Agent Tool Validation and Testing Strategies

### Individual Tool Testing

Test each agent tool independently to ensure proper functionality:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.todo_agents.tools.tool_implementations import create_todo_impl
from app.domain.todo_agents.tools.argument_models import CreateTodoArgs

@pytest.mark.asyncio
async def test_create_todo_tool_success():
    """Test the create_todo tool implementation."""
    # Mock the agent context
    mock_todo_service = AsyncMock()
    mock_todo_service.create_todo.return_value = MagicMock(id="test-id")

    # Set up tool context
    from app.domain.todo_agents.tools.tool_context import set_agent_context
    set_agent_context(
        todo_service=mock_todo_service,
        tag_service=AsyncMock(),
        user_id="test-user",
        quota_service=AsyncMock(),
        rate_limit_service=AsyncMock(),
    )

    # Test arguments
    args = CreateTodoArgs(
        title="Test Todo",
        description="Test description",
        importance="medium",
        tags=["test"]
    )

    # Execute tool
    result = await create_todo_impl(args)

    # Verify results
    assert result["success"] is True
    assert "todo_id" in result
    assert result["title"] == "Test Todo"
    mock_todo_service.create_todo.assert_called_once()
```

### Tool Integration Testing

```python
@pytest.mark.asyncio
async def test_agent_tool_chain_execution():
    """Test multiple tools working together in sequence."""

    # Mock all required services
    mock_todo_service = AsyncMock()
    mock_tag_service = AsyncMock()
    mock_quota_service = AsyncMock()
    mock_rate_limit_service = AsyncMock()

    # Set up realistic data
    mock_todo_service.create_todo.return_value = MagicMock(
        id="test-todo-id",
        title="Meeting with team",
        description="Weekly sync"
    )

    # Configure context
    set_agent_context(
        todo_service=mock_todo_service,
        tag_service=mock_tag_service,
        user_id="test-user-123",
        quota_service=mock_quota_service,
        rate_limit_service=mock_rate_limit_service,
    )

    # Create agent and run multi-step task
    from app.domain.todo_agents.tools.agent_factory import get_todo_agent

    agent = get_todo_agent()
    message = "Create a todo for weekly team meeting and schedule it for tomorrow"

    # Use mock runner to avoid actual AI calls
    mock_runner = AsyncMock()
    mock_runner.run.return_value = MagicMock(
        final_output="Todo created and scheduled successfully"
    )

    # Execute agent workflow
    result = await mock_runner.run(agent, message, max_turns=5)

    # Verify tool calls were made
    mock_todo_service.create_todo.assert_called()
    assert result.final_output == "Todo created and scheduled successfully"
```

### Tool Argument Validation Testing

```python
@pytest.mark.parametrize("invalid_args", [
    {"title": ""},  # Empty title
    {"importance": "invalid_level"},  # Invalid importance
    {"tags": ["tag_with spaces"]},  # Invalid tag format
])
def test_create_todo_argument_validation(invalid_args):
    """Test argument validation for create_todo tool."""
    with pytest.raises(ValidationError):
        CreateTodoArgs(**invalid_args)
```

## Mock AI Model Integration for Testing

### Mock Model Implementation

```python
from unittest.mock import AsyncMock, MagicMock
from agents.extensions.models.litellm_model import LitellmModel

class MockLitellmModel:
    """Mock LiteLLM model for testing agent interactions."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
        self.last_messages = []

    async def get_response(self, messages, **kwargs):
        """Mock response generation."""
        self.call_count += 1
        self.last_messages.append(messages)

        # Return predefined response or default
        if self.responses:
            response = self.responses.pop(0)
        else:
            response = self._generate_default_response(messages)

        return response

    def _generate_default_response(self, messages):
        """Generate default mock response based on last message."""
        last_message = messages[-1].get("content", "").lower()

        if "create todo" in last_message:
            return "I'll create a todo for you."
        elif "list todos" in last_message:
            return "Here are your current todos."
        elif "delete" in last_message:
            return "Todo deleted successfully."
        else:
            return "I understand your request."
```

### Mock Model Factory

```python
@pytest.fixture
def mock_agent_model():
    """Factory fixture for creating mock models."""
    def _create_model(responses=None):
        return MockLitellmModel(responses)
    return _create_model

@pytest.fixture
def configured_mock_agent(mock_agent_model):
    """Create a fully configured agent with mock model."""
    from app.domain.todo_agents.tools.agent_factory import get_todo_agent
    from agents import Agent

    # Patch the model in agent factory
    mock_model = mock_agent_model([
        "I'll create that todo for you.",
        "Here are your current todos.",
    ])

    with pytest.mock.patch('app.domain.todo_agents.tools.agent_factory.LitellmModel',
                          return_value=mock_model):
        agent = get_todo_agent()

    return agent, mock_model
```

### Testing with Mock Models

```python
@pytest.mark.asyncio
async def test_agent_workflow_with_mock_model(configured_mock_agent):
    """Test complete agent workflow using mock model."""
    agent, mock_model = configured_mock_agent

    # Create mock session
    mock_session = AsyncMock()

    # Test message
    test_message = "Create a todo for team meeting"

    # Run agent
    from agents import Runner
    result = await Runner.run(agent, test_message, session=mock_session)

    # Verify model was called
    assert mock_model.call_count > 0
    assert test_message in str(mock_model.last_messages)

    # Verify response
    assert "todo" in result.final_output.lower()
```

## Test Fixture Setup and Isolation Patterns

### Base Agent Test Fixture

```python
@pytest.fixture
async def agent_test_context():
    """Set up complete testing context for agent tests."""
    # Create mock services
    mock_todo_service = AsyncMock()
    mock_tag_service = AsyncMock()
    mock_quota_service = AsyncMock()
    mock_rate_limit_service = AsyncMock()

    # Configure realistic mock data
    mock_todo_service.create_todo.return_value = MagicMock(
        id="test-todo-123",
        title="Test Todo",
        description="Test Description"
    )

    mock_todo_service.list_todos.return_value = [
        MagicMock(id="todo-1", title="Existing Todo 1"),
        MagicMock(id="todo-2", title="Existing Todo 2"),
    ]

    # Configure quota service
    mock_quota_service.get_user_quota.return_value = {
        "used_requests": 10,
        "monthly_limit": 200,
        "remaining_quota": 190
    }

    # Set up agent context
    from app.domain.todo_agents.tools.tool_context import set_agent_context
    set_agent_context(
        todo_service=mock_todo_service,
        tag_service=mock_tag_service,
        user_id="test-user-123",
        quota_service=mock_quota_service,
        rate_limit_service=mock_rate_limit_service,
    )

    yield {
        "todo_service": mock_todo_service,
        "tag_service": mock_tag_service,
        "quota_service": mock_quota_service,
        "rate_limit_service": mock_rate_limit_service,
    }

    # Cleanup
    from app.domain.todo_agents.tools.tool_context import clear_agent_context
    clear_agent_context()
```

### Database Isolation for Agent Tests

```python
@pytest.fixture
async def isolated_agent_db():
    """Create isolated database for agent testing."""
    # Use in-memory SQLite for isolation
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session

    # Cleanup
    await engine.dispose()
```

### Session Management for Tests

```python
@pytest.fixture
def mock_agent_session():
    """Create mock SQLite session for testing."""
    from unittest.mock import AsyncMock, MagicMock

    session = AsyncMock()
    session.session_id = "test-session-123"

    # Mock session methods
    session.get_items.return_value = [
        {"role": "user", "content": "Create a todo"},
        {"role": "assistant", "content": "Todo created successfully"},
    ]

    session.clear_session.return_value = None

    return session

@pytest.fixture
def todo_agent_service(agent_test_context, mock_agent_session):
    """Create TodoAgentService with mocked dependencies."""
    from app.domain.todo_agents.services import TodoAgentService

    # Get context data
    context = agent_test_context

    # Create service with mocked dependencies
    service = TodoAgentService(
        todo_service=context["todo_service"],
        tag_service=context["tag_service"],
        rate_limit_service=context["rate_limit_service"],
        quota_service=context["quota_service"],
        session_db_path=":memory:",  # Use in-memory DB for tests
    )

    # Inject mock session
    service._sessions[mock_agent_session.session_id] = mock_agent_session

    return service
```

## Integration Testing for Agent Workflows

### End-to-End Agent Workflow Testing

```python
@pytest.mark.asyncio
async def test_complete_todo_agent_workflow(client, superuser_token_headers):
    """Test complete agent workflow from API to database."""

    # Test data
    agent_request = {
        "messages": [
            {"role": "user", "content": "Create a todo for team meeting tomorrow at 2 PM"}
        ],
        "session_id": "test-session-123"
    }

    # Mock the agent service to avoid AI calls
    with pytest.mock.patch('app.domain.todo_agents.controllers.todo_agents.TodoAgentService') as mock_service:
        mock_service_instance = AsyncMock()
        mock_service.return_value = mock_service_instance

        # Configure mock response
        mock_service_instance.chat_with_agent.return_value = (
            "I've created a todo for your team meeting tomorrow at 2 PM."
        )
        mock_service_instance.get_session_history.return_value = [
            {"role": "user", "content": "Create a todo for team meeting"},
            {"role": "assistant", "content": "Todo created successfully"}
        ]

        # Make API request
        response = await client.post(
            "/api/todo-agents/agent-create",
            json=agent_request,
            headers=superuser_token_headers
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "agent_response" in data

        # Verify service was called correctly
        mock_service_instance.chat_with_agent.assert_called_once_with(
            user_id="1",  # From superuser fixture
            message="Create a todo for team meeting tomorrow at 2 PM",
            session_id="test-session-123"
        )
```

### Streaming Response Testing

```python
@pytest.mark.asyncio
async def test_agent_streaming_workflow(client, superuser_token_headers):
    """Test agent streaming responses with Server-Sent Events."""

    agent_request = {
        "messages": [
            {"role": "user", "content": "List all my todos and schedule them"}
        ],
        "session_id": "test-stream-session"
    }

    # Mock streaming service
    async def mock_stream_events():
        yield {"event": "session_initialized", "data": {"session_id": "test-stream-session"}}
        yield {"event": "message_delta", "data": {"content": "Fetching "}}
        yield {"event": "message_delta", "data": {"content": "your todos..."}}
        yield {"event": "tool_call", "data": {"tool_name": "get_todo_list", "arguments": {}}}
        yield {"event": "tool_result", "data": {"output": "Found 3 todos"}}
        yield {"event": "completed", "data": {"final_message": "Found 3 todos in your list"}}
        yield {"event": "history", "data": [{"role": "assistant", "content": "Found 3 todos"}]}

    with pytest.mock.patch('app.domain.todo_agents.controllers.todo_agents.TodoAgentService') as mock_service:
        mock_service_instance = AsyncMock()
        mock_service.return_value = mock_service_instance
        mock_service_instance.stream_chat_with_agent.return_value = mock_stream_events()

        # Make streaming request
        response = await client.post(
            "/api/todo-agents/agent-create/stream",
            json=agent_request,
            headers=superuser_token_headers
        )

        # Verify streaming response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Collect and verify events
        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: ") or line.startswith("event: "):
                events.append(line)

        # Verify expected events were streamed
        event_types = [e.split(":")[0] for e in events if e.startswith("event: ")]
        assert "session_initialized" in event_types
        assert "completed" in event_types
        assert "history" in event_types
```

### Multi-Session Testing

```python
@pytest.mark.asyncio
async def test_agent_multi_session_isolation(todo_agent_service):
    """Test that agent sessions are properly isolated."""

    user1_id = "user-1"
    user2_id = "user-2"
    session1_id = "session-1"
    session2_id = "session-2"

    # User 1 creates a todo
    await todo_agent_service.chat_with_agent(
        user_id=user1_id,
        message="Create todo for user 1",
        session_id=session1_id
    )

    # User 2 creates a todo
    await todo_agent_service.chat_with_agent(
        user_id=user2_id,
        message="Create todo for user 2",
        session_id=session2_id
    )

    # Verify session isolation
    history1 = await todo_agent_service.get_session_history(session1_id)
    history2 = await todo_agent_service.get_session_history(session2_id)

    # Sessions should be separate
    assert len(history1) > 0
    assert len(history2) > 0

    # Verify content belongs to correct user
    user1_messages = [h for h in history1 if "user 1" in str(h).lower()]
    user2_messages = [h for h in history2 if "user 2" in str(h).lower()]

    assert len(user1_messages) > 0
    assert len(user2_messages) > 0
    assert len(user1_messages) == 0  # User 1 messages shouldn't be in session 2
    assert len(user2_messages) == 0  # User 2 messages shouldn't be in session 1
```

## Performance Testing and Benchmarking

### Agent Response Time Testing

```python
import time
import pytest
from statistics import mean, median

@pytest.mark.asyncio
async def test_agent_response_performance(todo_agent_service):
    """Benchmark agent response times for various operations."""

    test_operations = [
        ("Create simple todo", "Create a todo for meeting"),
        ("Create complex todo", "Create a todo for quarterly planning meeting with tag work and high importance"),
        ("List todos", "Show me all my todos"),
        ("Delete todo", "Delete todo with ID test-123"),
    ]

    response_times = []

    for operation_name, message in test_operations:
        start_time = time.time()

        try:
            result = await todo_agent_service.chat_with_agent(
                user_id="test-user",
                message=message,
                session_id=f"perf-test-{len(response_times)}"
            )

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append((operation_name, response_time))

            # Log performance data
            print(f"{operation_name}: {response_time:.2f}s")

        except Exception as e:
            print(f"Error in {operation_name}: {e}")
            continue

    # Performance assertions
    avg_response_time = mean(rt[1] for rt in response_times)
    assert avg_response_time < 5.0, f"Average response time {avg_response_time:.2f}s exceeds threshold"

    # Performance should be consistent
    max_response_time = max(rt[1] for rt in response_times)
    assert max_response_time < 10.0, f"Max response time {max_response_time:.2f}s exceeds threshold"
```

### Concurrent Load Testing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.asyncio
async def test_agent_concurrent_load(todo_agent_service):
    """Test agent performance under concurrent load."""

    async def single_user_simulation(user_id: int, message_count: int = 5):
        """Simulate a single user making multiple requests."""
        times = []
        errors = []

        for i in range(message_count):
            try:
                start_time = time.time()

                await todo_agent_service.chat_with_agent(
                    user_id=f"user-{user_id}",
                    message=f"Create todo number {i+1}",
                    session_id=f"user-{user_id}-session"
                )

                end_time = time.time()
                times.append(end_time - start_time)

            except Exception as e:
                errors.append(e)

        return {
            "user_id": user_id,
            "avg_time": mean(times) if times else 0,
            "max_time": max(times) if times else 0,
            "error_count": len(errors),
            "success_count": len(times)
        }

    # Simulate 10 concurrent users
    concurrent_users = 10
    tasks = [
        single_user_simulation(user_id)
        for user_id in range(concurrent_users)
    ]

    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict)]
    total_requests = sum(r["success_count"] for r in successful_results)
    total_errors = sum(r["error_count"] for r in successful_results)

    print(f"Concurrent test completed in {total_time:.2f}s")
    print(f"Total requests: {total_requests}, Errors: {total_errors}")
    print(f"Requests per second: {total_requests / total_time:.2f}")

    # Performance assertions
    error_rate = total_errors / (total_requests + total_errors) if (total_requests + total_errors) > 0 else 0
    assert error_rate < 0.1, f"Error rate {error_rate:.2%} exceeds 10%"
    assert total_requests >= 40, f"Too few successful requests: {total_requests}"
```

### Memory Usage Testing

```python
import psutil
import os

@pytest.mark.asyncio
async def test_agent_memory_usage(todo_agent_service):
    """Test agent memory consumption during extended operation."""

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Perform many operations
    operations = 50
    for i in range(operations):
        await todo_agent_service.chat_with_agent(
            user_id="memory-test-user",
            message=f"Create todo item {i+1}",
            session_id="memory-test-session"
        )

        # Check memory every 10 operations
        if i % 10 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            print(f"Operation {i}: Memory usage {current_memory:.1f}MB (+{memory_increase:.1f}MB)")

    final_memory = process.memory_info().rss / 1024 / 1024
    total_increase = final_memory - initial_memory

    print(f"Memory test completed: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{total_increase:.1f}MB)")

    # Memory should not increase excessively
    assert total_increase < 100, f"Memory increased by {total_increase:.1f}MB, exceeding threshold"
```

## Error Scenario Testing and Validation

### Network Error Handling

```python
@pytest.mark.asyncio
async def test_agent_network_error_handling(todo_agent_service):
    """Test agent behavior when network errors occur."""

    # Mock network failure
    from app.lib.exceptions import ApplicationError

    with pytest.mock.patch.object(todo_agent_service.todo_service, 'create_todo') as mock_create:
        mock_create.side_effect = ApplicationError("Network timeout occurred")

        result = await todo_agent_service.chat_with_agent(
            user_id="test-user",
            message="Create a new todo",
            session_id="error-test-session"
        )

        # Should handle error gracefully
        assert "error" in result.lower() or "failed" in result.lower()
        assert "network timeout" in result.lower()

@pytest.mark.asyncio
async def test_agent_quota_exceeded_handling(todo_agent_service):
    """Test agent behavior when user quota is exceeded."""

    # Mock quota service to return exceeded quota
    todo_agent_service.quota_service.get_user_quota.return_value = {
        "used_requests": 200,
        "monthly_limit": 200,
        "remaining_quota": 0
    }

    result = await todo_agent_service.chat_with_agent(
        user_id="quota-exceeded-user",
        message="Create a todo",
        session_id="quota-test"
    )

    # Should return user-friendly quota exceeded message
    assert "exceeded" in result.lower() and "limit" in result.lower()
```

### Invalid Input Handling

```python
@pytest.mark.asyncio
async def test_agent_invalid_input_handling(todo_agent_service):
    """Test agent behavior with invalid or malformed inputs."""

    invalid_inputs = [
        "",  # Empty message
        "   ",  # Whitespace only
        "Create todo without title",  # Vague instruction
        "Delete todo with invalid ID: abc-def-123",  # Invalid ID format
        "Schedule todo for invalid date: yesterday-2",  # Invalid date
    ]

    for invalid_input in invalid_inputs:
        result = await todo_agent_service.chat_with_agent(
            user_id="invalid-input-test",
            message=invalid_input,
            session_id=f"invalid-test-{hash(invalid_input)}"
        )

        # Should not crash and should provide meaningful response
        assert isinstance(result, str)
        assert len(result) > 0  # Should provide some response
```

### Tool Failure Handling

```python
@pytest.mark.asyncio
async def test_agent_tool_failure_handling():
    """Test agent behavior when tools fail."""

    # Mock tool failure
    with pytest.mock.patch('app.domain.todo_agents.tools.tool_implementations.create_todo_impl') as mock_create:
        mock_create.side_effect = Exception("Tool execution failed")

        # Set up context
        mock_todo_service = AsyncMock()
        set_agent_context(
            todo_service=mock_todo_service,
            tag_service=AsyncMock(),
            user_id="tool-failure-test",
            quota_service=AsyncMock(),
            rate_limit_service=AsyncMock(),
        )

        from app.domain.todo_agents.tools.agent_factory import get_todo_agent
        agent = get_todo_agent()

        # Agent should handle tool failure gracefully
        from agents import Runner
        result = await Runner.run(agent, "Create a todo for meeting", max_turns=3)

        # Should provide fallback response
        assert result.final_output is not None
        assert len(result.final_output) > 0
```

## Test Data Management and Fixtures

### Todo Data Fixtures

```python
@pytest.fixture
def sample_todos():
    """Sample todo data for testing."""
    return [
        {
            "id": "todo-1",
            "title": "Team Meeting",
            "description": "Weekly team sync",
            "importance": "high",
            "tags": ["work", "meeting"],
            "status": "pending"
        },
        {
            "id": "todo-2",
            "title": "Code Review",
            "description": "Review pull requests",
            "importance": "medium",
            "tags": ["work", "development"],
            "status": "in_progress"
        },
        {
            "id": "todo-3",
            "title": "Grocery Shopping",
            "description": "Buy groceries for the week",
            "importance": "low",
            "tags": ["personal", "shopping"],
            "status": "pending"
        }
    ]

@pytest.fixture
async def populated_todo_service(sample_todos):
    """Create a todo service populated with test data."""
    from app.domain.todo.services import TodoService

    # Mock service with sample data
    mock_service = AsyncMock()

    # Configure list_todos to return sample data
    mock_todos = [MagicMock(**todo) for todo in sample_todos]
    mock_service.list_todos.return_value = mock_todos

    # Configure individual todo retrieval
    def get_todo_by_id(todo_id):
        for todo in mock_todos:
            if todo.id == todo_id:
                return todo
        raise NotFoundError(f"Todo {todo_id} not found")

    mock_service.get_todo.side_effect = get_todo_by_id

    return mock_service
```

### Agent Conversation Fixtures

```python
@pytest.fixture
def sample_conversations():
    """Sample agent conversations for testing."""
    return {
        "simple_create": [
            {"role": "user", "content": "Create a todo for team meeting"},
            {"role": "assistant", "content": "I'll create a todo for your team meeting."}
        ],
        "complex_workflow": [
            {"role": "user", "content": "List my todos and schedule the high priority ones"},
            {"role": "assistant", "content": "Let me fetch your todos first."},
            {"role": "assistant", "content": "I found 5 todos. Scheduling the high priority ones..."},
        ],
        "error_recovery": [
            {"role": "user", "content": "Delete todo with invalid-id"},
            {"role": "assistant", "content": "I couldn't find a todo with that ID. Let me show you your current todos."}
        ]
    }

@pytest.fixture
def mock_session_data(sample_conversations):
    """Create mock session data with sample conversations."""
    return {
        "session-1": sample_conversations["simple_create"],
        "session-2": sample_conversations["complex_workflow"],
        "session-3": sample_conversations["error_recovery"]
    }
```

### Database Test Fixtures

```python
@pytest.fixture
async def test_database_with_agents():
    """Create test database with agent-related tables."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db.models import Base

    # Use test database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insert test data
    async with async_session() as session:
        # Add test users
        from app.db.models import User
        test_user = User(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            is_active=True
        )
        session.add(test_user)
        await session.commit()

    yield async_session

    # Cleanup
    await engine.dispose()
```

## Continuous Testing Strategies

### Automated Agent Regression Testing

```python
import pytest
from typing import Dict, List

class AgentTestSuite:
    """Automated test suite for agent regression testing."""

    def __init__(self):
        self.test_cases: Dict[str, List[dict]] = {
            "create_todo": [
                {"input": "Create a todo for meeting", "expected_keywords": ["created", "todo"]},
                {"input": "Add task for code review", "expected_keywords": ["added", "task"]},
            ],
            "list_todos": [
                {"input": "Show my todos", "expected_keywords": ["todos", "list"]},
                {"input": "What do I need to do?", "expected_keywords": ["tasks", "pending"]},
            ],
            "schedule_todos": [
                {"input": "Schedule meeting for tomorrow", "expected_keywords": ["scheduled", "tomorrow"]},
                {"input": "When should I do my tasks?", "expected_keywords": ["schedule", "time"]},
            ]
        }

    async def run_regression_tests(self, agent_service):
        """Run all regression tests against agent service."""
        results = {}

        for category, test_cases in self.test_cases.items():
            category_results = []

            for i, test_case in enumerate(test_cases):
                try:
                    response = await agent_service.chat_with_agent(
                        user_id="regression-test",
                        message=test_case["input"],
                        session_id=f"regression-{category}-{i}"
                    )

                    # Check if expected keywords are present
                    keywords_found = [
                        keyword for keyword in test_case["expected_keywords"]
                        if keyword.lower() in response.lower()
                    ]

                    success = len(keywords_found) > 0

                    category_results.append({
                        "input": test_case["input"],
                        "response": response,
                        "expected_keywords": test_case["expected_keywords"],
                        "keywords_found": keywords_found,
                        "success": success
                    })

                except Exception as e:
                    category_results.append({
                        "input": test_case["input"],
                        "error": str(e),
                        "success": False
                    })

            results[category] = category_results

        return results

@pytest.fixture
def agent_regression_suite():
    """Fixture providing automated regression test suite."""
    return AgentTestSuite()

@pytest.mark.asyncio
async def test_agent_regression(agent_regression_suite, todo_agent_service):
    """Run automated regression tests for agent."""

    results = await agent_regression_suite.run_regression_tests(todo_agent_service)

    # Analyze results
    total_tests = sum(len(tests) for tests in results.values())
    successful_tests = sum(
        sum(1 for test in tests if test.get("success", False))
        for tests in results.values()
    )

    success_rate = successful_tests / total_tests if total_tests > 0 else 0

    print(f"Regression test results: {successful_tests}/{total_tests} passed ({success_rate:.1%})")

    # Print failed tests for debugging
    for category, tests in results.items():
        failed_tests = [t for t in tests if not t.get("success", False)]
        if failed_tests:
            print(f"\nFailed tests in {category}:")
            for test in failed_tests:
                print(f"  - Input: {test['input']}")
                if "error" in test:
                    print(f"    Error: {test['error']}")
                else:
                    print(f"    Expected keywords not found: {test['expected_keywords']}")

    # Require at least 80% success rate
    assert success_rate >= 0.8, f"Regression test success rate {success_rate:.1%} below threshold"
```

### Continuous Integration Testing

```python
# ci_agent_tests.py - For CI/CD pipeline
import asyncio
import sys
from app.domain.todo_agents.services import TodoAgentService
from tests.agent_test_utils import create_mock_services, run_agent_tests

async def run_ci_agent_tests():
    """Run agent tests suitable for CI/CD environment."""

    try:
        # Create mock services for CI
        services = await create_mock_services()
        agent_service = TodoAgentService(**services)

        # Run test categories
        test_results = {
            "basic_functionality": await test_basic_functionality(agent_service),
            "error_handling": await test_error_scenarios(agent_service),
            "performance": await test_performance_benchmarks(agent_service),
            "regression": await run_regression_tests(agent_service),
        }

        # Evaluate results
        total_passed = sum(results["passed"] for results in test_results.values())
        total_tests = sum(results["total"] for results in test_results.values())

        if total_passed == total_tests:
            print(f"✅ All {total_tests} agent tests passed")
            return 0
        else:
            print(f"❌ {total_tests - total_passed} out of {total_tests} tests failed")
            return 1

    except Exception as e:
        print(f"❌ Agent tests failed with exception: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_ci_agent_tests())
    sys.exit(exit_code)
```

## Debug and Logging Strategies for Agents

### Agent Debug Logging Configuration

```python
import structlog
from typing import Any, Dict

class AgentDebugLogger:
    """Enhanced logging for agent debugging and monitoring."""

    def __init__(self):
        self.logger = structlog.get_logger("agent_debug")
        self.session_logs: Dict[str, List[Dict]] = {}

    def log_agent_request(self, session_id: str, user_id: str, message: str):
        """Log incoming agent request."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "agent_request",
            "session_id": session_id,
            "user_id": user_id,
            "message": message,
        }

        self.logger.info("Agent request received", **log_entry)
        self._add_to_session_log(session_id, log_entry)

    def log_tool_execution(self, session_id: str, tool_name: str, args: Dict, result: Any, execution_time: float):
        """Log tool execution details."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "tool_execution",
            "session_id": session_id,
            "tool_name": tool_name,
            "arguments": args,
            "result_summary": str(result)[:200],  # Truncate long results
            "execution_time_ms": execution_time * 1000,
        }

        self.logger.info("Tool executed", **log_entry)
        self._add_to_session_log(session_id, log_entry)

    def log_agent_response(self, session_id: str, response: str, total_time: float):
        """Log agent response."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "agent_response",
            "session_id": session_id,
            "response": response,
            "total_time_ms": total_time * 1000,
        }

        self.logger.info("Agent response generated", **log_entry)
        self._add_to_session_log(session_id, log_entry)

    def log_error(self, session_id: str, error: Exception, context: Dict):
        """Log errors with context."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "error",
            "session_id": session_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
        }

        self.logger.error("Agent error occurred", **log_entry)
        self._add_to_session_log(session_id, log_entry)

    def _add_to_session_log(self, session_id: str, log_entry: Dict):
        """Add log entry to session-specific log."""
        if session_id not in self.session_logs:
            self.session_logs[session_id] = []
        self.session_logs[session_id].append(log_entry)

    def get_session_debug_info(self, session_id: str) -> List[Dict]:
        """Get all debug information for a session."""
        return self.session_logs.get(session_id, [])

# Usage in TodoAgentService
agent_debug_logger = AgentDebugLogger()

async def chat_with_agent(self, user_id: str, message: str, session_id: str = None) -> str:
    """Enhanced chat_with_agent with debug logging."""
    session_id = session_id or f"user_{user_id}_{uuid.uuid4().hex[:8]}"
    start_time = time.time()

    try:
        # Log incoming request
        agent_debug_logger.log_agent_request(session_id, user_id, message)

        # ... existing logic ...

        # Log successful response
        total_time = time.time() - start_time
        agent_debug_logger.log_agent_response(session_id, result.final_output, total_time)

        return result.final_output

    except Exception as e:
        # Log error with context
        agent_debug_logger.log_error(
            session_id,
            e,
            {"user_id": user_id, "message": message}
        )
        raise
```

### Performance Monitoring

```python
import time
from dataclasses import dataclass
from typing import List

@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for agent operations."""
    session_id: str
    user_id: str
    operation: str
    start_time: float
    end_time: float
    tool_calls: List[str]
    success: bool
    error_message: str = None

class AgentPerformanceMonitor:
    """Monitor and analyze agent performance."""

    def __init__(self):
        self.metrics: List[AgentPerformanceMetrics] = []
        self.active_operations: Dict[str, float] = {}

    def start_operation(self, session_id: str, operation: str):
        """Start tracking an operation."""
        self.active_operations[f"{session_id}-{operation}"] = time.time()

    def end_operation(
        self,
        session_id: str,
        user_id: str,
        operation: str,
        tool_calls: List[str] = None,
        success: bool = True,
        error_message: str = None
    ):
        """End tracking an operation and record metrics."""
        key = f"{session_id}-{operation}"
        start_time = self.active_operations.pop(key, time.time())
        end_time = time.time()

        metric = AgentPerformanceMetrics(
            session_id=session_id,
            user_id=user_id,
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            tool_calls=tool_calls or [],
            success=success,
            error_message=error_message
        )

        self.metrics.append(metric)

    def get_performance_summary(self, user_id: str = None, hours: int = 24) -> Dict:
        """Get performance summary for analysis."""
        cutoff_time = time.time() - (hours * 3600)

        relevant_metrics = [
            m for m in self.metrics
            if m.start_time >= cutoff_time and (user_id is None or m.user_id == user_id)
        ]

        if not relevant_metrics:
            return {"message": "No metrics available for the specified period"}

        # Calculate statistics
        total_operations = len(relevant_metrics)
        successful_operations = len([m for m in relevant_metrics if m.success])
        avg_response_time = sum(m.end_time - m.start_time for m in relevant_metrics) / total_operations

        # Tool usage statistics
        tool_usage = {}
        for metric in relevant_metrics:
            for tool in metric.tool_calls:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1

        # Error analysis
        failed_operations = [m for m in relevant_metrics if not m.success]
        error_types = {}
        for metric in failed_operations:
            error_type = metric.error_message or "Unknown error"
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "period_hours": hours,
            "total_operations": total_operations,
            "success_rate": successful_operations / total_operations,
            "avg_response_time_seconds": avg_response_time,
            "tool_usage": tool_usage,
            "error_analysis": error_types,
            "most_used_tools": sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5],
        }

# Integration with TodoAgentService
performance_monitor = AgentPerformanceMonitor()

async def stream_chat_with_agent(self, user_id: str, message: str, session_id: str = None):
    """Enhanced streaming with performance monitoring."""
    session_id = session_id or f"user_{user_id}_{uuid.uuid4().hex[:8]}"

    # Start monitoring
    performance_monitor.start_operation(session_id, "stream_chat")
    tool_calls = []

    try:
        # ... existing streaming logic ...

        # Track tool calls in _dispatch_stream_event
        for event in stream.stream_events():
            if hasattr(event, 'item') and hasattr(event.item, 'tool_name'):
                tool_calls.append(event.item.tool_name)

            # ... rest of event handling ...

        # End monitoring with success
        performance_monitor.end_operation(
            session_id=session_id,
            user_id=user_id,
            operation="stream_chat",
            tool_calls=tool_calls,
            success=True
        )

    except Exception as e:
        # End monitoring with failure
        performance_monitor.end_operation(
            session_id=session_id,
            user_id=user_id,
            operation="stream_chat",
            tool_calls=tool_calls,
            success=False,
            error_message=str(e)
        )
        raise
```

### Debug Endpoints for Testing

```python
# Add to TodoAgentController for debugging in development
@get(path="/debug/sessions/{session_id:str}/logs", operation_id="debug_session_logs")
async def debug_session_logs(
    self,
    session_id: str,
    current_user: m.User,
) -> dict[str, Any]:
    """Get debug logs for a specific session (development only)."""

    if not settings.app.DEBUG:
        return {"error": "Debug endpoints only available in development mode"}

    # Get debug information
    debug_logs = agent_debug_logger.get_session_debug_info(session_id)

    # Get session history
    try:
        history = await self.todo_agent_service.get_session_history(session_id)
    except Exception as e:
        history = f"Error getting history: {e}"

    # Get performance metrics
    session_metrics = [
        m for m in performance_monitor.metrics
        if m.session_id == session_id
    ]

    return {
        "session_id": session_id,
        "debug_logs": debug_logs,
        "session_history": history,
        "performance_metrics": [
            {
                "operation": m.operation,
                "duration_seconds": m.end_time - m.start_time,
                "tool_calls": m.tool_calls,
                "success": m.success,
                "error": m.error_message
            }
            for m in session_metrics
        ]
    }

@get(path="/debug/performance", operation_id="debug_performance")
async def debug_performance(
    self,
    current_user: m.User,
    hours: int = 24,
) -> dict[str, Any]:
    """Get performance metrics for debugging (development only)."""

    if not settings.app.DEBUG:
        return {"error": "Debug endpoints only available in development mode"}

    summary = performance_monitor.get_performance_summary(
        user_id=str(current_user.id),
        hours=hours
    )

    return summary
```

This comprehensive documentation provides a complete testing framework for AI agents in the todo application, covering everything from unit testing to performance monitoring and debugging strategies. The patterns and examples can be adapted to specific testing needs and integrated into continuous testing pipelines.