# VolcEngine Doubao Integration

This document provides comprehensive documentation for integrating VolcEngine's Doubao AI service with the Todo application. It covers configuration, authentication, model integration, error handling, performance optimization, and security considerations.

## Table of Contents

1. [VolcEngine Doubao Service Overview](#volcengine-doubao-service-overview)
2. [API Configuration and Authentication Setup](#api-configuration-and-authentication-setup)
3. [Model Integration Patterns and Configuration](#model-integration-patterns-and-configuration)
4. [Request/Response Handling and Data Formats](#requestresponse-handling-and-data-formats)
5. [Error Handling and Retry Mechanisms](#error-handling-and-retry-mechanisms)
6. [Performance Optimization and Caching Strategies](#performance-optimization-and-caching-strategies)
7. [Cost Management and Usage Monitoring](#cost-management-and-usage-monitoring)
8. [Security Considerations and Data Privacy](#security-considerations-and-data-privacy)
9. [Integration Testing and Validation](#integration-testing-and-validation)
10. [Troubleshooting and Best Practices](#troubleshooting-and-best-practices)

## VolcEngine Doubao Service Overview

### What is VolcEngine Doubao?

VolcEngine Doubao is a large language model service provided by ByteDance (VolcEngine), offering advanced AI capabilities for natural language processing, content generation, and intelligent task automation. The service is designed to compete with other leading LLM providers and offers:

- **High Performance**: Optimized model responses with low latency
- **Chinese Language Excellence**: Specialized training for Chinese language understanding and generation
- **Multi-turn Conversations**: Advanced dialogue management capabilities
- **Function Calling**: Native support for tool/function invocation
- **Cost-Effective**: Competitive pricing for production workloads

### Key Capabilities

- **Natural Language Understanding**: Advanced comprehension of user intents
- **Content Generation**: High-quality text generation for various use cases
- **Tool Integration**: Built-in support for function calling and API integration
- **Multi-modal Processing**: Support for text and potentially other modalities
- **Context Management**: Long-term conversation memory and context preservation

### Integration Benefits

1. **Cost Efficiency**: Competitive pricing compared to other LLM providers
2. **Performance**: Low-latency responses suitable for real-time applications
3. **Language Support**: Excellent Chinese language capabilities
4. **Scalability**: Enterprise-grade infrastructure for production workloads
5. **Compliance**: Data processing compliance with regional regulations

## API Configuration and Authentication Setup

### Environment Configuration

The VolcEngine integration uses environment-based configuration for security and flexibility:

```bash
# .env file configuration
VOLCENGINE_API_KEY=your_volcengine_api_key_here
VOLCENGINE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/
```

### Application Settings Configuration

The configuration is managed through the centralized settings system:

```python
# src/app/config/base.py
@dataclass
class AISettings:
    """AI/LLM Client configurations."""

    VOLCENGINE_API_KEY: str | None = field(
        default_factory=get_env("VOLCENGINE_API_KEY", None))
    """VolcEngine API Key for Doubao models"""

    VOLCENGINE_BASE_URL: str | None = field(
        default_factory=get_env("VOLCENGINE_BASE_URL", None))
    """VolcEngine Base URL for API endpoints"""
```

### Authentication Pattern

VolcEngine uses API key-based authentication. The integration follows these patterns:

#### 1. Configuration Retrieval
```python
from app.config import get_settings

def get_volcengine_config():
    """Get VolcEngine configuration from settings."""
    settings = get_settings()
    return {
        "api_key": settings.ai.VOLCENGINE_API_KEY,
        "base_url": settings.ai.VOLCENGINE_BASE_URL
    }
```

#### 2. Client Initialization
```python
from agents.extensions.models.litellm_model import LitellmModel

def create_volcengine_model():
    """Create a LiteLLM model configured for VolcEngine Doubao."""
    settings = get_settings()

    if not settings.ai.VOLCENGINE_API_KEY or not settings.ai.VOLCENGINE_BASE_URL:
        raise ValueError("VolcEngine configuration is incomplete")

    return LitellmModel(
        model="openai/glm-4.5",  # Model identifier for VolcEngine
        api_key=settings.ai.VOLCENGINE_API_KEY,
        base_url=settings.ai.VOLCENGINE_BASE_URL,
    )
```

### Configuration Validation

```python
def validate_volcengine_config():
    """Validate that VolcEngine configuration is complete and accessible."""
    settings = get_settings()

    if not settings.ai.VOLCENGINE_API_KEY:
        raise ValueError("VOLCENGINE_API_KEY is required")

    if not settings.ai.VOLCENGINE_BASE_URL:
        raise ValueError("VOLCENGINE_BASE_URL is required")

    # Optional: Test connectivity
    try:
        import httpx
        response = httpx.get(
            settings.ai.VOLCENGINE_BASE_URL,
            headers={"Authorization": f"Bearer {settings.ai.VOLCENGINE_API_KEY}"},
            timeout=10
        )
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"VolcEngine API connectivity test failed: {e}")
```

## Model Integration Patterns and Configuration

### Agent Factory Integration

The VolcEngine model is integrated through the OpenAI Agents framework using the LiteLLM extension:

```python
# src/app/domain/todo_agents/tools/agent_factory.py
def get_todo_agent() -> Agent:
    """Create and return a configured todo agent with VolcEngine Doubao."""
    from agents import Agent
    from agents.extensions.models.litellm_model import LitellmModel

    settings = get_settings()

    model = LitellmModel(
        model="openai/glm-4.5",  # Maps to VolcEngine Doubao
        api_key=settings.ai.VOLCENGINE_API_KEY,
        base_url=settings.ai.VOLCENGINE_BASE_URL,
    )

    tools = cast("list[Tool]", list(get_tool_definitions()))

    return Agent(
        name="TodoAssistant",
        instructions=TODO_SYSTEM_INSTRUCTIONS,
        model=model,
        tools=tools,
    )
```

### Multi-Provider Support

The architecture supports multiple AI providers with a unified interface:

```python
class ModelProvider(Enum):
    """Available AI model providers."""
    VOLCENGINE = "volcengine"
    GLM = "glm"
    OPENAI = "openai"

def create_model(provider: ModelProvider = ModelProvider.VOLCENGINE):
    """Create a model instance based on the specified provider."""
    settings = get_settings()

    if provider == ModelProvider.VOLCENGINE:
        return LitellmModel(
            model="openai/glm-4.5",
            api_key=settings.ai.VOLCENGINE_API_KEY,
            base_url=settings.ai.VOLCENGINE_BASE_URL,
        )
    elif provider == ModelProvider.GLM:
        return LitellmModel(
            model="openai/glm-4.5",
            api_key=settings.ai.GLM_API_KEY,
            base_url=settings.ai.GLM_BASE_URL,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

### Model Configuration Parameters

The VolcEngine model supports various configuration parameters:

```python
def get_volcengine_model_config():
    """Get comprehensive VolcEngine model configuration."""
    return {
        "model": "openai/glm-4.5",  # Model identifier
        "api_key": get_settings().ai.VOLCENGINE_API_KEY,
        "base_url": get_settings().ai.VOLCENGINE_BASE_URL,
        "temperature": 0.7,  # Response creativity (0.0-2.0)
        "max_tokens": 4000,  # Maximum response tokens
        "top_p": 0.9,  # Nucleus sampling parameter
        "frequency_penalty": 0.0,  # Repetition penalty
        "presence_penalty": 0.0,  # Presence penalty
        "timeout": 30.0,  # Request timeout in seconds
        "max_retries": 3,  # Maximum retry attempts
    }
```

### Dynamic Model Selection

```python
def get_model_for_user(user_id: str) -> LitellmModel:
    """Select appropriate model based on user preferences or system load."""
    # Implementation could consider:
    # - User preferences
    # - System load balancing
    # - Cost optimization
    # - Regional availability

    # For now, default to VolcEngine
    return create_model(ModelProvider.VOLCENGINE)
```

## Request/Response Handling and Data Formats

### Standard Request Format

The integration uses OpenAI-compatible request format through LiteLLM:

```python
class VolcEngineRequest:
    """Standard request format for VolcEngine API."""

    def __init__(
        self,
        messages: list[dict[str, Any]],
        model: str = "openai/glm-4.5",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        tools: list[dict[str, Any]] | None = None,
        **kwargs
    ):
        self.messages = messages
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tools = tools or []
        self.kwargs = kwargs

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary format."""
        return {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **({"tools": self.tools} if self.tools else {}),
            **self.kwargs
        }
```

### Message Format

```python
class ConversationMessage:
    """Standard conversation message format."""

    def __init__(
        self,
        role: str,  # "system", "user", "assistant", "tool"
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None
    ):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.name = name

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary format."""
        result = {
            "role": self.role,
            "content": self.content
        }

        if self.tool_calls:
            result["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        if self.name:
            result["name"] = self.name

        return result
```

### Tool/Function Calling Format

```python
class ToolCall:
    """Tool call format for function execution."""

    def __init__(
        self,
        id: str,
        type: str = "function",
        function: dict[str, Any] | None = None
    ):
        self.id = id
        self.type = type
        self.function = function or {}

    @classmethod
    def create_function_call(
        cls,
        call_id: str,
        name: str,
        arguments: str
    ) -> "ToolCall":
        """Create a function call tool."""
        return cls(
            id=call_id,
            function={
                "name": name,
                "arguments": arguments
            }
        )
```

### Response Handling

```python
class VolcEngineResponse:
    """Standard response format for VolcEngine API."""

    def __init__(self, response_data: dict[str, Any]):
        self.id = response_data.get("id")
        self.object = response_data.get("object", "chat.completion")
        self.created = response_data.get("created")
        self.model = response_data.get("model")
        self.choices = response_data.get("choices", [])
        self.usage = response_data.get("usage", {})

    @property
    def content(self) -> str:
        """Get the primary response content."""
        if self.choices:
            return self.choices[0].get("message", {}).get("content", "")
        return ""

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        """Get tool calls from the response."""
        if self.choices:
            return self.choices[0].get("message", {}).get("tool_calls", [])
        return []

    @property
    def finish_reason(self) -> str:
        """Get the finish reason for the response."""
        if self.choices:
            return self.choices[0].get("finish_reason", "")
        return ""

    def get_usage_info(self) -> dict[str, int]:
        """Get token usage information."""
        return {
            "prompt_tokens": self.usage.get("prompt_tokens", 0),
            "completion_tokens": self.usage.get("completion_tokens", 0),
            "total_tokens": self.usage.get("total_tokens", 0),
        }
```

### Streaming Response Handling

```python
class StreamingResponseHandler:
    """Handler for streaming responses from VolcEngine."""

    def __init__(self):
        self.buffer = []
        self.tool_calls = []
        self.content = ""

    def process_chunk(self, chunk: dict[str, Any]) -> dict[str, Any] | None:
        """Process a streaming response chunk."""
        choices = chunk.get("choices", [])

        if not choices:
            return None

        delta = choices[0].get("delta", {})

        # Handle content chunks
        if "content" in delta and delta["content"]:
            self.content += delta["content"]
            return {
                "type": "content",
                "content": delta["content"]
            }

        # Handle tool call chunks
        if "tool_calls" in delta:
            for tool_call_delta in delta["tool_calls"]:
                self._process_tool_call_delta(tool_call_delta)

            return {
                "type": "tool_call",
                "tool_calls": delta["tool_calls"]
            }

        # Handle finish
        if choices[0].get("finish_reason"):
            return {
                "type": "finish",
                "reason": choices[0].get("finish_reason"),
                "content": self.content,
                "tool_calls": self.tool_calls
            }

        return None

    def _process_tool_call_delta(self, delta: dict[str, Any]):
        """Process tool call delta for streaming responses."""
        tool_call_index = delta.get("index", 0)

        # Ensure tool_calls list has enough elements
        while len(self.tool_calls) <= tool_call_index:
            self.tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})

        tool_call = self.tool_calls[tool_call_index]

        if "id" in delta:
            tool_call["id"] = delta["id"]

        if "function" in delta:
            function_delta = delta["function"]

            if "name" in function_delta:
                tool_call["function"]["name"] = function_delta["name"]

            if "arguments" in function_delta:
                tool_call["function"]["arguments"] += function_delta["arguments"]
```

## Error Handling and Retry Mechanisms

### Error Classification

The integration implements comprehensive error handling for different types of failures:

```python
from enum import Enum
from typing import Any, Dict

class VolcEngineErrorType(Enum):
    """Classification of VolcEngine API errors."""
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    INVALID_REQUEST = "invalid_request"
    MODEL_ERROR = "model_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"

class VolcEngineError(Exception):
    """Custom exception for VolcEngine API errors."""

    def __init__(
        self,
        message: str,
        error_type: VolcEngineErrorType,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code
        self.response_data = response_data or {}

    @classmethod
    def from_response(cls, response_data: dict[str, Any], status_code: int) -> "VolcEngineError":
        """Create error instance from API response."""
        error_info = response_data.get("error", {})
        message = error_info.get("message", "Unknown error")
        error_type_str = error_info.get("type", "unknown_error")

        # Map API error types to our enum
        error_type_mapping = {
            "invalid_api_key": VolcEngineErrorType.AUTHENTICATION_ERROR,
            "insufficient_quota": VolcEngineErrorType.RATE_LIMIT_ERROR,
            "invalid_request": VolcEngineErrorType.INVALID_REQUEST,
            "model_not_found": VolcEngineErrorType.MODEL_ERROR,
            "rate_limit_exceeded": VolcEngineErrorType.RATE_LIMIT_ERROR,
        }

        error_type = error_type_mapping.get(
            error_type_str,
            VolcEngineErrorType.UNKNOWN_ERROR
        )

        return cls(
            message=message,
            error_type=error_type,
            status_code=status_code,
            response_data=response_data
        )
```

### Retry Strategy

```python
import asyncio
import random
from functools import wraps
from typing import Any, Callable

class RetryConfig:
    """Configuration for retry mechanisms."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter to avoid thundering herd
            delay *= (0.5 + random.random() * 0.5)

        return delay

def volcengine_retry(config: RetryConfig = None):
    """Decorator for retrying VolcEngine API calls."""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except VolcEngineError as e:
                    last_exception = e

                    # Don't retry certain error types
                    if e.error_type in [
                        VolcEngineErrorType.AUTHENTICATION_ERROR,
                        VolcEngineErrorType.INVALID_REQUEST
                    ]:
                        break

                    # Don't retry on last attempt
                    if attempt >= config.max_attempts:
                        break

                    delay = config.get_delay(attempt)
                    await asyncio.sleep(delay)

                except Exception as e:
                    last_exception = e
                    # Retry unknown errors
                    if attempt >= config.max_attempts:
                        break

                    delay = config.get_delay(attempt)
                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator
```

### Error Handling Implementation

```python
import httpx
from typing import Any, Dict, Optional

class VolcEngineClient:
    """Robust VolcEngine API client with error handling."""

    def __init__(self, config: dict[str, Any]):
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.retry_config = RetryConfig()

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(30.0, connect=10.0)
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    @volcengine_retry()
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        **kwargs
    ) -> dict[str, Any]:
        """Create chat completion with error handling."""
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": kwargs.get("model", "openai/glm-4.5"),
                    "messages": messages,
                    **{k: v for k, v in kwargs.items() if k != "model"}
                }
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
            except:
                error_data = {"error": {"message": str(e)}}

            raise VolcEngineError.from_response(error_data, e.response.status_code)

        except httpx.RequestError as e:
            raise VolcEngineError(
                message=f"Network error: {e}",
                error_type=VolcEngineErrorType.NETWORK_ERROR
            )

        except Exception as e:
            raise VolcEngineError(
                message=f"Unexpected error: {e}",
                error_type=VolcEngineErrorType.UNKNOWN_ERROR
            )

    @volcengine_retry()
    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        **kwargs
    ):
        """Create streaming chat completion with error handling."""
        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": kwargs.get("model", "openai/glm-4.5"),
                    "messages": messages,
                    "stream": True,
                    **{k: v for k, v in kwargs.items() if k != "model"}
                }
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
            except:
                error_data = {"error": {"message": str(e)}}

            raise VolcEngineError.from_response(error_data, e.response.status_code)

        except httpx.RequestError as e:
            raise VolcEngineError(
                message=f"Network error: {e}",
                error_type=VolcEngineErrorType.NETWORK_ERROR
            )
```

### Circuit Breaker Pattern

```python
import asyncio
from datetime import datetime, timedelta

class CircuitBreaker:
    """Circuit breaker for preventing cascade failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func):
        """Decorator to apply circuit breaker to a function."""
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise VolcEngineError(
                        "Circuit breaker is OPEN",
                        error_type=VolcEngineErrorType.SERVER_ERROR
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result

            except self.expected_exception as e:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.last_failure_time is None:
            return True

        return (
            datetime.now() - self.last_failure_time
        ) >= timedelta(seconds=self.recovery_timeout)

    def _on_success(self):
        """Handle successful function call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed function call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

## Performance Optimization and Caching Strategies

### Response Caching

```python
import hashlib
import json
from typing import Any, Optional
from functools import lru_cache
from datetime import datetime, timedelta

class ResponseCache:
    """Intelligent response caching for VolcEngine API calls."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        cache_key_prefix: str = "volcengine"
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache_key_prefix = cache_key_prefix
        self.cache = {}

    def _generate_cache_key(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate cache key from request parameters."""
        # Create a deterministic representation of the request
        request_data = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Use only the last few messages to avoid overly specific caching
        if len(messages) > 3:
            request_data["messages"] = messages[-3:]

        request_str = json.dumps(request_data, sort_keys=True)
        hash_obj = hashlib.sha256(request_str.encode())

        return f"{self.cache_key_prefix}:{hash_obj.hexdigest()}"

    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Get cached response."""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]

            # Check if cache item is still valid
            if datetime.now() - cached_item["timestamp"] < timedelta(seconds=self.ttl_seconds):
                return cached_item["response"]
            else:
                # Remove expired item
                del self.cache[cache_key]

        return None

    def set(self, cache_key: str, response: dict[str, Any]):
        """Cache response."""
        # Evict old items if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[cache_key] = {
            "response": response,
            "timestamp": datetime.now()
        }

    def _evict_oldest(self):
        """Remove oldest cached item."""
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k]["timestamp"]
        )
        del self.cache[oldest_key]

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()

# Usage with the client
class CachedVolcEngineClient:
    """VolcEngine client with caching support."""

    def __init__(self, config: dict[str, Any], cache: Optional[ResponseCache] = None):
        self.client = VolcEngineClient(config)
        self.cache = cache or ResponseCache()

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str = "openai/glm-4.5",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        use_cache: bool = True
    ) -> dict[str, Any]:
        """Chat completion with caching."""
        if use_cache:
            cache_key = self.cache._generate_cache_key(
                messages, model, temperature, max_tokens
            )

            # Try to get from cache
            cached_response = self.cache.get(cache_key)
            if cached_response:
                return cached_response

        # Make API call
        response = await self.client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Cache the response
        if use_cache and response:
            cache_key = self.cache._generate_cache_key(
                messages, model, temperature, max_tokens
            )
            self.cache.set(cache_key, response)

        return response
```

### Connection Pooling and Keep-Alive

```python
class OptimizedVolcEngineClient:
    """Optimized client with connection pooling."""

    def __init__(self, config: dict[str, Any]):
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]

        # Optimized HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Connection": "keep-alive"
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            ),
            http2=True  # Enable HTTP/2 for better performance
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
```

### Request Batching

```python
from typing import List
import asyncio

class BatchProcessor:
    """Batch processing for multiple VolcEngine requests."""

    def __init__(
        self,
        client: OptimizedVolcEngineClient,
        batch_size: int = 5,
        delay_between_batches: float = 0.1
    ):
        self.client = client
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches

    async def process_batch(
        self,
        requests: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        """Process multiple requests in batches."""
        results = []

        for i in range(0, len(requests), self.batch_size):
            batch = requests[i:i + self.batch_size]

            # Process batch concurrently
            batch_tasks = []
            for request in batch:
                task = self.client.chat_completion(**request)
                batch_tasks.append(task)

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)

            # Small delay between batches to avoid rate limiting
            if i + self.batch_size < len(requests):
                await asyncio.sleep(self.delay_between_batches)

        return results
```

### Performance Monitoring

```python
import time
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PerformanceMetrics:
    """Performance metrics for VolcEngine API calls."""
    request_count: int = 0
    total_response_time: float = 0.0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        return self.total_response_time / max(self.request_count, 1)

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return self.error_count / max(self.request_count, 1)

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_cache_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total_cache_requests, 1)

class PerformanceMonitor:
    """Monitor performance of VolcEngine API calls."""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.request_times: List[float] = []

    def record_request(self, response_time: float, success: bool, cache_hit: bool = False):
        """Record a request's performance metrics."""
        self.metrics.request_count += 1
        self.metrics.total_response_time += response_time
        self.request_times.append(response_time)

        if not success:
            self.metrics.error_count += 1

        if cache_hit:
            self.metrics.cache_hits += 1
        else:
            self.metrics.cache_misses += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "request_count": self.metrics.request_count,
            "average_response_time": self.metrics.average_response_time,
            "error_rate": self.metrics.error_rate,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "p95_response_time": self._calculate_percentile(95),
            "p99_response_time": self._calculate_percentile(99),
        }

    def _calculate_percentile(self, percentile: float) -> float:
        """Calculate response time percentile."""
        if not self.request_times:
            return 0.0

        sorted_times = sorted(self.request_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]

# Usage decorator
def monitor_performance(monitor: PerformanceMonitor):
    """Decorator to monitor function performance."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            cache_hit = kwargs.get("cache_hit", False)

            try:
                result = await func(*args, **kwargs)
                success = True
                return result

            finally:
                response_time = time.time() - start_time
                monitor.record_request(response_time, success, cache_hit)

        return wrapper
    return decorator
```

## Cost Management and Usage Monitoring

### Token Usage Tracking

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

@dataclass
class TokenUsage:
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    timestamp: datetime
    user_id: str

    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on token usage."""
        # VolcEngine Doubao pricing (example rates - update with actual rates)
        pricing = {
            "openai/glm-4.5": {
                "prompt_per_1k": 0.0015,   # $0.0015 per 1K prompt tokens
                "completion_per_1k": 0.002,  # $0.002 per 1K completion tokens
            }
        }

        model_pricing = pricing.get(self.model, pricing["openai/glm-4.5"])

        prompt_cost = (self.prompt_tokens / 1000) * model_pricing["prompt_per_1k"]
        completion_cost = (self.completion_tokens / 1000) * model_pricing["completion_per_1k"]

        return prompt_cost + completion_cost

class UsageTracker:
    """Track and analyze VolcEngine API usage."""

    def __init__(self):
        self.usage_history: List[TokenUsage] = []
        self.daily_limits: Dict[str, float] = {}
        self.monthly_limits: Dict[str, float] = {}

    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        user_id: str
    ):
        """Record token usage for a request."""
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
            timestamp=datetime.now(),
            user_id=user_id
        )

        self.usage_history.append(usage)

        # Keep only last 90 days of history
        cutoff_date = datetime.now() - timedelta(days=90)
        self.usage_history = [
            u for u in self.usage_history if u.timestamp > cutoff_date
        ]

    def get_daily_usage(self, user_id: str, date: datetime = None) -> Dict[str, Any]:
        """Get daily usage statistics for a user."""
        if date is None:
            date = datetime.now()

        day_usage = [
            u for u in self.usage_history
            if u.user_id == user_id and u.timestamp.date() == date.date()
        ]

        return self._calculate_usage_stats(day_usage)

    def get_monthly_usage(self, user_id: str, year: int = None, month: int = None) -> Dict[str, Any]:
        """Get monthly usage statistics for a user."""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        month_usage = [
            u for u in self.usage_history
            if (
                u.user_id == user_id and
                u.timestamp.year == year and
                u.timestamp.month == month
            )
        ]

        return self._calculate_usage_stats(month_usage)

    def _calculate_usage_stats(self, usage_list: List[TokenUsage]) -> Dict[str, Any]:
        """Calculate usage statistics for a list of usage records."""
        if not usage_list:
            return {
                "total_requests": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "average_tokens_per_request": 0.0
            }

        total_prompt = sum(u.prompt_tokens for u in usage_list)
        total_completion = sum(u.completion_tokens for u in usage_list)
        total_tokens = sum(u.total_tokens for u in usage_list)
        total_cost = sum(u.cost_estimate for u in usage_list)

        return {
            "total_requests": len(usage_list),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "estimated_cost": total_cost,
            "average_tokens_per_request": total_tokens / len(usage_list),
            "models_used": list(set(u.model for u in usage_list))
        }

    def check_limits(self, user_id: str) -> Dict[str, Any]:
        """Check if user is approaching or has exceeded usage limits."""
        today_usage = self.get_daily_usage(user_id)
        this_month_usage = self.get_monthly_usage(user_id)

        daily_limit = self.daily_limits.get(user_id, float('inf'))
        monthly_limit = self.monthly_limits.get(user_id, float('inf'))

        daily_usage_pct = (today_usage["total_tokens"] / daily_limit * 100) if daily_limit != float('inf') else 0
        monthly_usage_pct = (this_month_usage["total_tokens"] / monthly_limit * 100) if monthly_limit != float('inf') else 0

        return {
            "daily_usage": today_usage,
            "monthly_usage": this_month_usage,
            "daily_limit": daily_limit,
            "monthly_limit": monthly_limit,
            "daily_usage_percentage": daily_usage_pct,
            "monthly_usage_percentage": monthly_usage_pct,
            "warnings": self._generate_warnings(daily_usage_pct, monthly_usage_pct)
        }

    def _generate_warnings(self, daily_pct: float, monthly_pct: float) -> List[str]:
        """Generate usage warnings based on percentage."""
        warnings = []

        if daily_pct >= 100:
            warnings.append("Daily usage limit exceeded")
        elif daily_pct >= 80:
            warnings.append("Approaching daily usage limit")

        if monthly_pct >= 100:
            warnings.append("Monthly usage limit exceeded")
        elif monthly_pct >= 80:
            warnings.append("Approaching monthly usage limit")

        return warnings
```

### Rate Limiting and Quota Management

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

class RateLimiter:
    """Rate limiting for VolcEngine API calls."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 3000,
        tokens_per_minute: int = 40000,
        tokens_per_hour: int = 200000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.tokens_per_minute = tokens_per_minute
        self.tokens_per_hour = tokens_per_hour

        self.request_history: List[datetime] = []
        self.token_usage_history: List[Dict[str, Any]] = []

    async def check_rate_limit(
        self,
        user_id: str,
        tokens_requested: int = 0
    ) -> bool:
        """Check if request is within rate limits."""
        now = datetime.now()

        # Clean old history
        self._cleanup_history(now)

        # Check request limits
        recent_requests = [r for r in self.request_history if r > now - timedelta(minutes=1)]
        if len(recent_requests) >= self.requests_per_minute:
            return False

        recent_requests_hour = [r for r in self.request_history if r > now - timedelta(hours=1)]
        if len(recent_requests_hour) >= self.requests_per_hour:
            return False

        # Check token limits
        recent_tokens = [
            t for t in self.token_usage_history
            if t["timestamp"] > now - timedelta(minutes=1)
        ]
        tokens_last_minute = sum(t["tokens"] for t in recent_tokens)
        if tokens_last_minute + tokens_requested >= self.tokens_per_minute:
            return False

        recent_tokens_hour = [
            t for t in self.token_usage_history
            if t["timestamp"] > now - timedelta(hours=1)
        ]
        tokens_last_hour = sum(t["tokens"] for t in recent_tokens_hour)
        if tokens_last_hour + tokens_requested >= self.tokens_per_hour:
            return False

        # Record this request
        self.request_history.append(now)
        self.token_usage_history.append({
            "timestamp": now,
            "tokens": tokens_requested,
            "user_id": user_id
        })

        return True

    def _cleanup_history(self, now: datetime):
        """Remove old request history."""
        # Keep only last hour of request history
        cutoff_time = now - timedelta(hours=1)
        self.request_history = [r for r in self.request_history if r > cutoff_time]
        self.token_usage_history = [
            t for t in self.token_usage_history if t["timestamp"] > cutoff_time
        ]

    def get_wait_time(self, tokens_requested: int = 0) -> float:
        """Get estimated wait time until next request can be made."""
        now = datetime.now()

        # Calculate wait time based on request limits
        recent_requests = [r for r in self.request_history if r > now - timedelta(minutes=1)]
        if len(recent_requests) >= self.requests_per_minute:
            oldest_request = min(recent_requests)
            wait_time_requests = (oldest_request + timedelta(minutes=1) - now).total_seconds()
        else:
            wait_time_requests = 0

        # Calculate wait time based on token limits
        recent_tokens = [
            t for t in self.token_usage_history
            if t["timestamp"] > now - timedelta(minutes=1)
        ]
        tokens_last_minute = sum(t["tokens"] for t in recent_tokens)

        if tokens_last_minute + tokens_requested >= self.tokens_per_minute:
            # Estimate when tokens will be available
            if recent_tokens:
                oldest_token = min(t["timestamp"] for t in recent_tokens)
                wait_time_tokens = (oldest_token + timedelta(minutes=1) - now).total_seconds()
            else:
                wait_time_tokens = 0
        else:
            wait_time_tokens = 0

        return max(wait_time_requests, wait_time_tokens)
```

### Budget Management

```python
class BudgetManager:
    """Manage API usage budget and alerts."""

    def __init__(self):
        self.budgets: Dict[str, Dict[str, Any]] = {}
        self.alert_thresholds = {
            "warning": 0.7,  # 70% of budget
            "critical": 0.9,  # 90% of budget
            "exceeded": 1.0   # 100% of budget
        }

    def set_budget(
        self,
        user_id: str,
        daily_budget: float,
        monthly_budget: float,
        alert_emails: List[str] = None
    ):
        """Set budget limits for a user."""
        self.budgets[user_id] = {
            "daily": daily_budget,
            "monthly": monthly_budget,
            "alert_emails": alert_emails or [],
            "alerts_sent": {
                "daily": {"warning": False, "critical": False, "exceeded": False},
                "monthly": {"warning": False, "critical": False, "exceeded": False}
            }
        }

    def check_budget_status(
        self,
        user_id: str,
        usage_tracker: UsageTracker
    ) -> Dict[str, Any]:
        """Check budget status for a user."""
        if user_id not in self.budgets:
            return {"status": "no_budget_set"}

        budget = self.budgets[user_id]
        daily_usage = usage_tracker.get_daily_usage(user_id)
        monthly_usage = usage_tracker.get_monthly_usage(user_id)

        daily_pct = daily_usage["estimated_cost"] / budget["daily"] if budget["daily"] > 0 else 0
        monthly_pct = monthly_usage["estimated_cost"] / budget["monthly"] if budget["monthly"] > 0 else 0

        status = {
            "daily": {
                "used": daily_usage["estimated_cost"],
                "budget": budget["daily"],
                "percentage": daily_pct,
                "remaining": max(0, budget["daily"] - daily_usage["estimated_cost"])
            },
            "monthly": {
                "used": monthly_usage["estimated_cost"],
                "budget": budget["monthly"],
                "percentage": monthly_pct,
                "remaining": max(0, budget["monthly"] - monthly_usage["estimated_cost"])
            }
        }

        # Check alerts
        alerts = self._check_alerts(user_id, daily_pct, monthly_pct)
        if alerts:
            status["alerts"] = alerts

        return status

    def _check_alerts(self, user_id: str, daily_pct: float, monthly_pct: float) -> List[str]:
        """Check if any budget alerts should be triggered."""
        alerts = []
        budget = self.budgets[user_id]

        # Daily alerts
        for level, threshold in self.alert_thresholds.items():
            if daily_pct >= threshold and not budget["alerts_sent"]["daily"][level]:
                alerts.append(f"daily_{level}")
                budget["alerts_sent"]["daily"][level] = True

        # Monthly alerts
        for level, threshold in self.alert_thresholds.items():
            if monthly_pct >= threshold and not budget["alerts_sent"]["monthly"][level]:
                alerts.append(f"monthly_{level}")
                budget["alerts_sent"]["monthly"][level] = True

        return alerts
```

## Security Considerations and Data Privacy

### API Key Management

```python
import os
from cryptography.fernet import Fernet
from typing import Optional

class SecureKeyManager:
    """Secure management of API keys."""

    def __init__(self, encryption_key: Optional[bytes] = None):
        if encryption_key is None:
            # Generate or load encryption key
            key_file = os.path.join(os.path.expanduser("~"), ".volcengine_key")
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    encryption_key = f.read()
            else:
                encryption_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(encryption_key)
                # Set restrictive file permissions
                os.chmod(key_file, 0o600)

        self.cipher_suite = Fernet(encryption_key)

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for storage."""
        return self.cipher_suite.encrypt(api_key.encode()).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for usage."""
        return self.cipher_suite.decrypt(encrypted_key.encode()).decode()

    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key format."""
        # VolcEngine API keys are typically UUID format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, api_key, re.IGNORECASE))
```

### Data Sanitization

```python
import re
import html
from typing import Any, Dict, List

class DataSanitizer:
    """Sanitize data to prevent security issues."""

    # Patterns to detect and remove sensitive information
    SENSITIVE_PATTERNS = [
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CREDIT_CARD]'),  # Credit card
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_ADDRESS]'),  # IP addresses
        (r'\bhttps?://[^\s<>"{}|\\^`\[\]]+\b', '[URL]'),  # URLs
        (r'\b[A-Z]{2}\d{2}[A-Z\d]{4}\b', '[PASSPORT]'),  # Passport numbers
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitize text content by removing sensitive information."""
        if not isinstance(text, str):
            return str(text)

        sanitized = html.escape(text)  # Escape HTML

        # Remove sensitive patterns
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
        """Sanitize dictionary values."""
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_text(value)
            elif isinstance(value, dict) and deep:
                sanitized[key] = cls.sanitize_dict(value, deep)
            elif isinstance(value, list) and deep:
                sanitized[key] = [
                    cls.sanitize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_log_data(cls, data: Any) -> Any:
        """Sanitize data for logging."""
        if isinstance(data, str):
            return cls.sanitize_text(data)
        elif isinstance(data, dict):
            # Remove or mask sensitive fields
            sensitive_fields = {
                'api_key', 'password', 'token', 'secret',
                'authorization', 'auth', 'credential'
            }

            sanitized = {}
            for key, value in data.items():
                if key.lower() in sensitive_fields:
                    sanitized[key] = '[REDACTED]'
                elif isinstance(value, dict):
                    sanitized[key] = cls.sanitize_log_data(value)
                elif isinstance(value, list):
                    sanitized[key] = [
                        cls.sanitize_log_data(item) for item in value
                    ]
                elif isinstance(value, str):
                    sanitized[key] = cls.sanitize_text(value)
                else:
                    sanitized[key] = value

            return sanitized

        return data
```

### Request/Response Filtering

```python
from typing import List, Set

class SecurityFilter:
    """Security filter for API requests and responses."""

    def __init__(self):
        # Blocked patterns for input validation
        self.blocked_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'union\s+select',  # SQL injection
            r'drop\s+table',  # SQL injection
            r'insert\s+into',  # SQL injection
        ]

        # Allowed domains for content filtering
        self.allowed_domains: Set[str] = set()

        # Rate limiting per IP
        self.ip_request_counts: Dict[str, List[datetime]] = {}

    def validate_input(self, content: str) -> bool:
        """Validate input content against security rules."""
        if not content:
            return True

        content_lower = content.lower()

        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return False

        # Check for potential prompt injection
        injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'disregard\s+the\s+above',
            r'system\s*:',
            r'assistant\s*:',
            r'\[START\]',
            r'\[BEGIN\]',
        ]

        for pattern in injection_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return False

        return True

    def filter_response(self, response: str) -> str:
        """Filter response content for security."""
        if not response:
            return response

        # Remove any potential system instructions in responses
        filtered = re.sub(
            r'(?i)(system\s*:\s*|assistant\s*:\s*)(.*?)(?=\n|$)',
            lambda m: f'{m.group(1)}[FILTERED]',
            response
        )

        # Remove any code execution instructions
        filtered = re.sub(
            r'(?i)(execute|run|eval)\s*[\(\[]',
            '[BLOCKED_EXECUTION]',
            filtered
        )

        return filtered

    def check_ip_rate_limit(self, ip_address: str, max_requests: int = 100, window_minutes: int = 10) -> bool:
        """Check IP-based rate limiting."""
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=window_minutes)

        # Clean old records
        if ip_address in self.ip_request_counts:
            self.ip_request_counts[ip_address] = [
                req_time for req_time in self.ip_request_counts[ip_address]
                if req_time > cutoff_time
            ]
        else:
            self.ip_request_counts[ip_address] = []

        # Check current request count
        if len(self.ip_request_counts[ip_address]) >= max_requests:
            return False

        # Record this request
        self.ip_request_counts[ip_address].append(now)
        return True
```

### Audit Logging

```python
import logging
from datetime import datetime
from typing import Any, Dict, Optional

class AuditLogger:
    """Audit logging for VolcEngine API interactions."""

    def __init__(self, log_file: str = "volcengine_audit.log"):
        self.logger = logging.getLogger("volcengine_audit")
        self.logger.setLevel(logging.INFO)

        # Create file handler
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log_request(
        self,
        user_id: str,
        session_id: str,
        request_data: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        """Log API request."""
        sanitized_request = DataSanitizer.sanitize_log_data(request_data)

        log_entry = {
            "event": "api_request",
            "user_id": user_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
            "request": sanitized_request
        }

        self.logger.info(f"REQUEST: {json.dumps(log_entry)}")

    def log_response(
        self,
        user_id: str,
        session_id: str,
        response_data: Dict[str, Any],
        response_time: float,
        tokens_used: int = 0
    ):
        """Log API response."""
        sanitized_response = DataSanitizer.sanitize_log_data(response_data)

        log_entry = {
            "event": "api_response",
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": response_time * 1000,
            "tokens_used": tokens_used,
            "response": sanitized_response
        }

        self.logger.info(f"RESPONSE: {json.dumps(log_entry)}")

    def log_error(
        self,
        user_id: str,
        session_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log API error."""
        log_entry = {
            "event": "api_error",
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": DataSanitizer.sanitize_log_data(context or {})
        }

        self.logger.error(f"ERROR: {json.dumps(log_entry)}")

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Log security-related events."""
        log_entry = {
            "event": "security_event",
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": DataSanitizer.sanitize_log_data(details)
        }

        self.logger.warning(f"SECURITY: {json.dumps(log_entry)}")
```

## Integration Testing and Validation

### Test Configuration

```python
import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any

class VolcEngineTestConfig:
    """Test configuration for VolcEngine integration."""

    @staticmethod
    def get_test_config() -> Dict[str, Any]:
        """Get test configuration."""
        return {
            "api_key": "test-api-key-12345",
            "base_url": "https://api.test.volces.com/api/v3/",
            "model": "openai/glm-4.5",
            "timeout": 30.0,
            "max_retries": 2
        }

    @staticmethod
    def get_mock_response() -> Dict[str, Any]:
        """Get mock API response."""
        return {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "openai/glm-4.5",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response from VolcEngine Doubao."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        }

@pytest.fixture
def volcengine_config():
    """Pytest fixture for VolcEngine configuration."""
    return VolcEngineTestConfig.get_test_config()

@pytest.fixture
def mock_volcengine_response():
    """Pytest fixture for mock VolcEngine response."""
    return VolcEngineTestConfig.get_mock_response()
```

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestVolcEngineClient:
    """Unit tests for VolcEngine client."""

    @pytest.fixture
    def client(self, volcengine_config):
        """Create test client."""
        return VolcEngineClient(volcengine_config)

    @patch('httpx.AsyncClient.post')
    async def test_chat_completion_success(self, mock_post, client, mock_volcengine_response):
        """Test successful chat completion."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_volcengine_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        messages = [{"role": "user", "content": "Hello"}]
        result = await client.chat_completion(messages)

        # Assertions
        assert result["id"] == "chatcmpl-test123"
        assert result["choices"][0]["message"]["content"] == "This is a test response from VolcEngine Doubao."
        mock_post.assert_called_once()

    @patch('httpx.AsyncClient.post')
    async def test_chat_completion_authentication_error(self, mock_post, client):
        """Test authentication error handling."""
        # Setup mock for 401 error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid API key",
                "type": "invalid_api_key"
            }
        }
        mock_post.return_value = mock_response

        # Test and assert
        with pytest.raises(VolcEngineError) as exc_info:
            await client.chat_completion([{"role": "user", "content": "Hello"}])

        assert exc_info.value.error_type == VolcEngineErrorType.AUTHENTICATION_ERROR

    @patch('httpx.AsyncClient.post')
    async def test_rate_limit_error(self, mock_post, client):
        """Test rate limit error handling."""
        # Setup mock for 429 error
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
                "type": "rate_limit_exceeded"
            }
        }
        mock_post.return_value = mock_response

        # Test and assert
        with pytest.raises(VolcEngineError) as exc_info:
            await client.chat_completion([{"role": "user", "content": "Hello"}])

        assert exc_info.value.error_type == VolcEngineErrorType.RATE_LIMIT_ERROR

class TestRetryMechanism:
    """Unit tests for retry mechanism."""

    @patch('httpx.AsyncClient.post')
    async def test_retry_on_transient_error(self, mock_post, volcengine_config, mock_volcengine_response):
        """Test retry behavior on transient errors."""
        # Setup mock to fail twice then succeed
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.json.return_value = {"error": {"message": "Service unavailable"}}

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = mock_volcengine_response
        mock_response_success.raise_for_status.return_value = None

        mock_post.side_effect = [
            httpx.HTTPStatusError("Service Unavailable", request=MagicMock(), response=mock_response_fail),
            httpx.HTTPStatusError("Service Unavailable", request=MagicMock(), response=mock_response_fail),
            mock_response_success
        ]

        # Create client with retry configuration
        client = VolcEngineClient(volcengine_config)
        client.retry_config = RetryConfig(max_attempts=3)

        # Test
        messages = [{"role": "user", "content": "Hello"}]
        result = await client.chat_completion(messages)

        # Assertions
        assert result["id"] == "chatcmpl-test123"
        assert mock_post.call_count == 3  # 2 failures + 1 success
```

### Integration Tests

```python
import pytest
from app.domain.todo_agents.tools.agent_factory import get_todo_agent
from app.domain.todo_agents.services import TodoAgentService

class TestVolcEngineIntegration:
    """Integration tests for VolcEngine Doubao integration."""

    @pytest.mark.asyncio
    async def test_agent_integration(self):
        """Test full agent integration with VolcEngine."""
        # Setup
        settings = get_settings()

        # Skip test if VolcEngine credentials are not available
        if not settings.ai.VOLCENGINE_API_KEY or not settings.ai.VOLCENGINE_BASE_URL:
            pytest.skip("VolcEngine credentials not configured for testing")

        # Create agent
        agent = get_todo_agent()

        # Test basic conversation
        response = await Runner.run(
            agent,
            "Hello, can you help me create a todo?",
            max_turns=5
        )

        # Assertions
        assert response.final_output
        assert isinstance(response.final_output, str)
        assert len(response.final_output) > 0

    @pytest.mark.asyncio
    async def test_service_integration(self):
        """Test service layer integration."""
        # This would require setting up test services and database
        # Implementation would depend on your service architecture
        pass

    @pytest.mark.asyncio
    async def test_streaming_integration(self):
        """Test streaming response integration."""
        settings = get_settings()

        if not settings.ai.VOLCENGINE_API_KEY:
            pytest.skip("VolcEngine credentials not configured for testing")

        # Test streaming functionality
        agent = get_todo_agent()
        stream = Runner.run_streamed(
            agent,
            "Tell me about creating todos",
            max_turns=3
        )

        events_received = []
        async for event in stream.stream_events():
            events_received.append(event)

        # Assertions
        assert len(events_received) > 0
```

### Load Testing

```python
import asyncio
import time
from typing import List

class LoadTester:
    """Load testing for VolcEngine integration."""

    def __init__(self, client: VolcEngineClient):
        self.client = client

    async def run_concurrent_requests(
        self,
        num_requests: int = 10,
        messages: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Run concurrent requests to test performance."""
        if messages is None:
            messages = [{"role": "user", "content": "Hello, test message"}]

        start_time = time.time()

        # Create concurrent tasks
        tasks = [
            self.client.chat_completion(messages.copy())
            for _ in range(num_requests)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # Analyze results
        successful_requests = [r for r in results if not isinstance(r, Exception)]
        failed_requests = [r for r in results if isinstance(r, Exception)]

        return {
            "total_requests": num_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "average_response_time": total_time / num_requests,
            "success_rate": len(successful_requests) / num_requests * 100,
            "errors": [str(e) for e in failed_requests]
        }

# Example usage in tests
@pytest.mark.asyncio
async def test_load_performance(volcengine_config):
    """Test load performance of VolcEngine integration."""
    client = VolcEngineClient(volcengine_config)
    load_tester = LoadTester(client)

    # Test with moderate load
    results = await load_tester.run_concurrent_requests(num_requests=5)

    # Assertions for reasonable performance
    assert results["success_rate"] >= 80  # At least 80% success rate
    assert results["requests_per_second"] >= 0.5  # At least 0.5 requests per second

    await client.close()
```

## Troubleshooting and Best Practices

### Common Issues and Solutions

#### 1. Authentication Failures

**Problem**: API key authentication failures
```python
# Error: {"error": {"message": "Invalid API key", "type": "invalid_api_key"}}
```

**Solutions**:
```python
def troubleshoot_authentication():
    """Troubleshoot authentication issues."""

    # 1. Verify API key format
    settings = get_settings()
    api_key = settings.ai.VOLCENGINE_API_KEY

    if not api_key:
        print("ERROR: VOLCENGINE_API_KEY not configured")
        return

    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', api_key):
        print("ERROR: Invalid API key format")
        return

    # 2. Test API connectivity
    try:
        import httpx
        response = httpx.get(
            settings.ai.VOLCENGINE_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        print(f"API connectivity test: {response.status_code}")
    except Exception as e:
        print(f"API connectivity failed: {e}")
```

#### 2. Rate Limiting Issues

**Problem**: Rate limiting errors
```python
# Error: {"error": {"message": "Rate limit exceeded", "type": "rate_limit_exceeded"}}
```

**Solutions**:
```python
async def handle_rate_limiting(client: VolcEngineClient):
    """Handle rate limiting gracefully."""

    # Implement exponential backoff
    retry_config = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0
    )

    @volcengine_retry(retry_config)
    async def make_request_with_retry():
        return await client.chat_completion([
            {"role": "user", "content": "Test message"}
        ])

    try:
        return await make_request_with_retry()
    except VolcEngineError as e:
        if e.error_type == VolcEngineErrorType.RATE_LIMIT_ERROR:
            # Wait longer before retrying
            wait_time = 60  # Wait 1 minute
            print(f"Rate limited. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            return await make_request_with_retry()
        raise
```

#### 3. Network Connectivity Issues

**Problem**: Network timeouts or connection errors

**Solutions**:
```python
def troubleshoot_network():
    """Troubleshoot network connectivity issues."""

    settings = get_settings()

    # 1. Check base URL accessibility
    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            response = client.get(settings.ai.VOLCENGINE_BASE_URL)
            print(f"Base URL accessible: {response.status_code}")
    except Exception as e:
        print(f"Base URL not accessible: {e}")

    # 2. Check DNS resolution
    import socket
    hostname = settings.ai.VOLCENGINE_BASE_URL.split('//')[1].split('/')[0]
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"DNS resolution successful: {hostname} -> {ip_address}")
    except socket.gaierror as e:
        print(f"DNS resolution failed: {e}")

    # 3. Check firewall/proxy settings
    print("Check if firewall or proxy is blocking requests to VolcEngine")
```

### Performance Optimization Checklist

#### 1. Connection Management
```python
# Use connection pooling
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=10,
        max_connections=20,
        keepalive_expiry=30.0
    ),
    http2=True  # Enable HTTP/2
)

# Reuse connections when possible
class VolcEnginePool:
    def __init__(self, max_clients: int = 5):
        self.clients = asyncio.Queue(maxsize=max_clients)
        self.semaphore = asyncio.Semaphore(max_clients)

    async def get_client(self):
        await self.semaphore.acquire()
        try:
            return await self.clients.get()
        except asyncio.QueueEmpty:
            return VolcEngineClient(get_settings().ai.__dict__)

    async def return_client(self, client):
        try:
            await self.clients.put(client)
        except asyncio.QueueFull:
            await client.close()
        finally:
            self.semaphore.release()
```

#### 2. Request Optimization
```python
# Optimize request parameters
def optimize_request_params():
    """Optimize request parameters for better performance."""
    return {
        "temperature": 0.7,  # Balanced creativity and consistency
        "max_tokens": 2000,  # Reasonable response length
        "top_p": 0.9,        # Nucleus sampling
        "frequency_penalty": 0.0,  # No repetition penalty for factual responses
        "presence_penalty": 0.0,   # No presence penalty
        "stream": False,  # Disable streaming unless needed
    }

# Batch similar requests
class RequestBatcher:
    def __init__(self, batch_size: int = 5, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []

    async def add_request(self, request_data: dict):
        """Add request to batch."""
        self.pending_requests.append(request_data)

        if len(self.pending_requests) >= self.batch_size:
            return await self.process_batch()

        return None

    async def process_batch(self):
        """Process batched requests."""
        if not self.pending_requests:
            return []

        batch = self.pending_requests.copy()
        self.pending_requests.clear()

        # Process batch concurrently
        tasks = [self._process_single_request(req) for req in batch]
        return await asyncio.gather(*tasks)
```

#### 3. Caching Strategy
```python
# Implement intelligent caching
class SmartCache:
    def __init__(self):
        self.cache = {}
        self.response_patterns = {}

    def should_cache(self, messages: list[dict]) -> bool:
        """Determine if response should be cached."""
        # Don't cache very unique requests
        if len(messages) == 1 and len(messages[0]["content"]) > 100:
            return False

        # Cache requests with high similarity to previous ones
        content = " ".join(msg["content"] for msg in messages)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # If similar content was requested before, cache this one
        similar_requests = sum(1 for pattern in self.response_patterns.values()
                             if self._calculate_similarity(content, pattern) > 0.8)

        return similar_requests > 0

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0
```

### Monitoring and Alerting

```python
class HealthMonitor:
    """Monitor VolcEngine integration health."""

    def __init__(self):
        self.error_counts = {}
        self.response_times = []
        self.last_health_check = None

    async def health_check(self, client: VolcEngineClient) -> dict:
        """Perform health check on VolcEngine integration."""
        try:
            start_time = time.time()

            # Test simple request
            response = await client.chat_completion([
                {"role": "user", "content": "Health check"}
            ], max_tokens=10)

            response_time = time.time() - start_time
            self.response_times.append(response_time)

            # Keep only last 100 response times
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]

            self.last_health_check = datetime.now()

            return {
                "status": "healthy",
                "response_time": response_time,
                "average_response_time": sum(self.response_times) / len(self.response_times),
                "last_check": self.last_health_check.isoformat()
            }

        except Exception as e:
            error_type = type(e).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": error_type,
                "error_count": self.error_counts[error_type],
                "last_check": datetime.now().isoformat()
            }

    def get_health_summary(self) -> dict:
        """Get health monitoring summary."""
        return {
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "total_errors": sum(self.error_counts.values()),
            "error_breakdown": self.error_counts,
            "average_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else None,
            "response_count": len(self.response_times)
        }

# Alerting system
class AlertManager:
    """Manage alerts for VolcEngine integration issues."""

    def __init__(self, alert_webhook_url: str = None):
        self.alert_webhook_url = alert_webhook_url
        self.alert_history = []

    async def send_alert(self, alert_type: str, message: str, severity: str = "warning"):
        """Send alert notification."""
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }

        self.alert_history.append(alert)

        # Send webhook notification if configured
        if self.alert_webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(self.alert_webhook_url, json=alert)
            except Exception as e:
                print(f"Failed to send alert webhook: {e}")

        # Log alert
        logger.warning(f"ALERT: {alert_type} - {message}")
```

### Best Practices Summary

#### 1. Configuration Management
- Use environment variables for all sensitive configuration
- Implement configuration validation at startup
- Support multiple deployment environments
- Regularly rotate API keys

#### 2. Error Handling
- Implement comprehensive error classification
- Use exponential backoff for retries
- Never retry authentication or invalid request errors
- Log all errors with sufficient context

#### 3. Performance Optimization
- Enable HTTP/2 and connection pooling
- Implement intelligent caching
- Use streaming for long responses
- Monitor and optimize request patterns

#### 4. Security
- Validate and sanitize all inputs
- Implement rate limiting per user/IP
- Encrypt sensitive data at rest
- Log all security events

#### 5. Monitoring
- Track token usage and costs
- Monitor response times and error rates
- Implement health checks
- Set up alerts for critical issues

#### 6. Testing
- Unit tests for all components
- Integration tests with real API
- Load testing for performance validation
- Mock testing for CI/CD pipelines

This comprehensive documentation provides all the necessary information for successfully integrating VolcEngine Doubao with your Todo application, including practical code examples, troubleshooting guides, and best practices for production deployment.