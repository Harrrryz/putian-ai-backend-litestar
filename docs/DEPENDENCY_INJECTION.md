# Dependency Injection System

This document provides comprehensive documentation for the dependency injection (DI) system used in this Litestar application. The DI system provides clean separation of concerns, testability, and modular architecture through sophisticated dependency management patterns.

## Table of Contents

1. [Litestar Dependency Injection Framework](#litestar-dependency-injection-framework)
2. [Core Dependency Infrastructure](#core-dependency-infrastructure)
3. [Service Provider Patterns](#service-provider-patterns)
4. [Database Session Injection](#database-session-injection)
5. [Authentication and Authorization Dependencies](#authentication-and-authorization-dependencies)
6. [Configuration Dependency Injection](#configuration-dependency-injection)
7. [Custom Service Dependencies](#custom-service-dependencies)
8. [Request-Scoped vs Application-Scoped Dependencies](#request-scoped-vs-application-scoped-dependencies)
9. [Testing with Dependency Injection](#testing-with-dependency-injection)
10. [Advanced Patterns and Best Practices](#advanced-patterns-and-best-practices)

## Litestar Dependency Injection Framework

This application leverages Litestar's built-in dependency injection system, which provides:

- **Type-safe dependency resolution** through function annotations
- **Automatic dependency discovery** via parameter type hints
- **Scope-aware dependency management** (request, application, session scopes)
- **Dependency caching** for performance optimization
- **Async/sync dependency support**

### Basic DI Pattern

```python
from litestar import Controller, get
from litestar.di import Provide

class MyController(Controller):
    # Controller-level dependency registration
    dependencies = {
        "my_service": Provide(provide_my_service),
    }

    @get()
    async def my_endpoint(self, my_service: MyService) -> Response:
        # Dependency automatically injected
        result = await my_service.do_something()
        return result
```

## Core Dependency Infrastructure

The application builds upon Litestar's DI system with custom infrastructure in `src/app/lib/deps.py`:

```python
"""Application dependency providers generators."""

from advanced_alchemy.extensions.litestar.providers import (
    DependencyCache,
    DependencyDefaults,
    create_filter_dependencies,
    create_service_dependencies,
    create_service_provider,
    dep_cache,
)

__all__ = (
    "DependencyCache",
    "DependencyDefaults",
    "create_filter_dependencies",
    "create_service_dependencies",
    "create_service_provider",
    "dep_cache",
)
```

### Key Components

- **`create_service_provider`**: Factory for creating service dependency providers
- **`create_filter_dependencies`**: Creates filter-based dependencies for data querying
- **`dep_cache`**: Dependency caching mechanism for performance optimization
- **`DependencyCache`**: Type-safe dependency cache implementation
- **`DependencyDefaults`**: Default dependency configuration

## Service Provider Patterns

The application uses sophisticated service provider patterns to create dependency injection functions for domain services.

### Standard Service Provider

```python
# src/app/domain/accounts/deps.py
provide_users_service = create_service_provider(
    UserService,
    load=[
        selectinload(m.User.roles).options(
            joinedload(m.UserRole.role, innerjoin=True)),
        selectinload(m.User.oauth_accounts),
    ],
    error_messages={
        "duplicate_key": "This user already exists.",
        "integrity": "User operation failed.",
    },
)
```

### Key Features

1. **Eager Loading Configuration**: Optimized database queries with strategic loading strategies
2. **Error Message Customization**: Domain-specific error messages
3. **Repository Configuration**: Customized repository behavior
4. **Type Safety**: Full type annotation support

### Controller Integration

```python
class UserController(Controller):
    dependencies = {
        "users_service": Provide(provide_users_service),
    } | create_filter_dependencies({
        "id_filter": UUID,
        "search": "name,email",
        "pagination_type": "limit_offset",
        "pagination_size": 20,
        "created_at": True,
        "updated_at": True,
        "sort_field": "name",
        "sort_order": "asc",
    })
```

## Database Session Injection

The application uses Advanced Alchemy's session management with custom session providers.

### SQLAlchemy Session Provider

```python
# src/app/config/app.py
alchemy = SQLAlchemyAsyncConfig(
    engine_instance=settings.db.get_engine(),
    before_send_handler="autocommit",
    session_config=AsyncSessionConfig(expire_on_commit=False),
    alembic_config=AlembicAsyncConfig(
        version_table_name=settings.db.MIGRATION_DDL_VERSION_TABLE,
        script_config=settings.db.MIGRATION_CONFIG,
        script_location=settings.db.MIGRATION_PATH,
    ),
)
```

### Custom Database Session

For OpenAI Agents integration, the application provides a custom `DatabaseSession` class:

```python
# src/app/lib/database_session.py
class DatabaseSession:
    """Custom session implementation following the OpenAI Agents SDK Session protocol."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        db_session: AsyncSession,
        agent_name: str | None = None,
        agent_instructions: str | None = None,
        session_name: str | None = None,
    ) -> None:
        # Initialize with database session and metadata
        self.session_id = session_id
        self.user_id = user_id
        self.db_session = db_session
        # ... additional initialization
```

## Authentication and Authorization Dependencies

The authentication system implements comprehensive security dependencies.

### JWT Authentication Provider

```python
# src/app/domain/accounts/guards.py
async def current_user_from_token(
    token: Token,
    connection: ASGIConnection[Any, Any, Any, Any]
) -> m.User | None:
    """Lookup current user from local JWT token."""
    service = await anext(provide_users_service(alchemy.provide_session(connection.app.state, connection.scope)))
    user = await service.get_one_or_none(email=token.sub)
    return user if user and user.is_active and user.is_verified else None

auth = OAuth2PasswordBearerAuth[m.User](
    retrieve_user_handler=current_user_from_token,
    token_secret=settings.app.SECRET_KEY,
    token_url=urls.ACCOUNT_LOGIN,
    exclude=[
        constants.HEALTH_ENDPOINT,
        urls.ACCOUNT_LOGIN,
        # ... additional excluded routes
    ],
)
```

### Authorization Guards

```python
def requires_active_user(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Request requires active user."""
    if connection.user.is_active:
        return
    msg = "Inactive account"
    raise PermissionDeniedException(msg)

def requires_superuser(
    connection: ASGIConnection[m.User, Any, Any, Any],
    _: BaseRouteHandler
) -> None:
    """Request requires active superuser."""
    if connection.user.is_superuser:
        return
    raise PermissionDeniedException(detail="Insufficient privileges")

def requires_verified_user(
    connection: ASGIConnection[m.User, Any, Any, Any],
    _: BaseRouteHandler
) -> None:
    """Verify the connection user is verified."""
    if connection.user.is_verified:
        return
    raise PermissionDeniedException(detail="User account is not verified.")
```

### Current User Provider

```python
# src/app/domain/accounts/deps.py
async def provide_user(request: Request[m.User, Any, Any]) -> m.User:
    """Get the user from the request."""
    return request.user

# Global registration in ApplicationCore
dependencies = {"current_user": Provide(provide_user)}
```

## Configuration Dependency Injection

Configuration is managed through a centralized settings system with dependency injection support.

### Settings Provider

```python
# src/app/config/base.py
@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    # ... additional configuration sections

@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env()

# Usage in dependencies
settings = get_settings()
```

### Environment-Based Configuration

```python
# Configuration with environment variable support
@dataclass
class DatabaseSettings:
    URL: str = field(default_factory=get_env("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3"))
    ECHO: bool = field(default_factory=get_env("DATABASE_ECHO", False))
    POOL_SIZE: int = field(default_factory=get_env("DATABASE_POOL_SIZE", 5))
    # ... additional database configuration
```

## Custom Service Dependencies

The application implements domain-specific service dependencies with sophisticated provider patterns.

### Domain Service Provider

```python
# src/app/domain/todo_agents/deps.py
async def provide_todo_agent_service(
    todo_service: "TodoService",
    tag_service: "TagService",
    rate_limit_service: "RateLimitService",
    quota_service: "UserUsageQuotaService",
) -> "TodoAgentService":
    """Dependency provider for TodoAgentService."""
    return create_todo_agent_service(
        todo_service=todo_service,
        tag_service=tag_service,
        rate_limit_service=rate_limit_service,
        quota_service=quota_service,
    )
```

### Multi-Dependency Service

```python
# src/app/domain/agent_sessions/deps.py
provide_agent_session_service = create_service_provider(
    AgentSessionService,
    load=[
        joinedload(m.AgentSession.user, innerjoin=True),
        selectinload(m.AgentSession.messages),
    ],
    error_messages={
        "duplicate_key": "Agent session with this session_id already exists for this user.",
        "integrity": "Agent session operation failed.",
    },
)
```

### Controller-Level Dependencies

```python
class TodoController(Controller):
    dependencies = {
        "todo_service": Provide(provide_todo_service),
        "tag_service": Provide(provide_tag_service),
    } | create_filter_dependencies({
        "id_filter": UUID,
        "search": "item",
        "pagination_type": "limit_offset",
        "pagination_size": 40,
        "created_at": True,
        "updated_at": True,
        "sort_field": "created_time",
        "sort_order": "asc",
    })
```

## Request-Scoped vs Application-Scoped Dependencies

The application distinguishes between different dependency scopes:

### Request-Scoped Dependencies

- **Database Sessions**: New session per request
- **Current User**: User context specific to request
- **Custom Services**: Services with per-request state

```python
# Request-scoped database session
async def provide_db_session(connection: ASGIConnection) -> AsyncSession:
    """Provide request-scoped database session."""
    return alchemy.provide_session(connection.app.state, connection.scope)
```

### Application-Scoped Dependencies

- **Configuration**: Singleton settings instance
- **Rate Limiting**: Application-wide rate limiting service
- **Cache Services**: Shared cache instances

```python
# Application-scoped service
@lru_cache(maxsize=1, typed=True)
def get_rate_limit_service() -> RateLimitService:
    """Get cached rate limit service."""
    return RateLimitService()
```

### Dependency Scope Configuration

```python
# Global dependencies in ApplicationCore
dependencies = {
    "current_user": Provide(provide_user, sync_to_thread=False),
    "settings": Provide(get_settings, sync_to_thread=True),  # Cached
}
```

## Testing with Dependency Injection

The application provides comprehensive testing utilities for dependency injection scenarios.

### Test Configuration Override

```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: MonkeyPatch) -> None:
    """Patch settings for testing."""
    settings = base.Settings.from_env(".env.testing")

    def get_settings(dotenv_filename: str = ".env.testing") -> base.Settings:
        return settings

    monkeypatch.setattr(base, "get_settings", get_settings)
```

### Service Mocking

```python
# Example test with dependency mocking
async def test_user_creation_with_mock_service():
    """Test user creation with mocked service."""
    mock_service = AsyncMock(spec=UserService)
    mock_service.create.return_value = MockUser(id=uuid.uuid4())

    # Override dependency for test
    with override_dependency("users_service", mock_service):
        response = await client.post("/users", json={"email": "test@example.com"})

    assert response.status_code == 201
    mock_service.create.assert_called_once()
```

### Database Dependency Testing

```python
@pytest.fixture
async def test_db_session():
    """Provide test database session."""
    async with TestDatabaseSession() as session:
        yield session

async def test_todo_service_integration(test_db_session):
    """Test todo service with test database."""
    service = TodoService(session=test_db_session)
    result = await service.create({"item": "Test Todo", "user_id": test_user.id})
    assert result.item == "Test Todo"
```

## Advanced Patterns and Best Practices

### 1. Dependency Factories

```python
# Factory pattern for complex dependencies
def create_service_dependency(
    service_class: type,
    load_options: list = None,
    error_messages: dict = None,
):
    """Factory for creating service dependencies."""
    return create_service_provider(
        service_class,
        load=load_options or [],
        error_messages=error_messages or {},
    )
```

### 2. Conditional Dependencies

```python
# Conditional dependency based on configuration
async def provide_storage_service() -> StorageService:
    """Provide storage service based on configuration."""
    settings = get_settings()
    if settings.storage.USE_S3:
        return S3StorageService(settings.aws)
    else:
        return LocalStorageService(settings.storage)
```

### 3. Dependency Composition

```python
# Composing multiple dependencies
async def provide_agent_service(
    db_session: AsyncSession,
    storage_service: StorageService,
    rate_limiter: RateLimitService,
) -> AgentService:
    """Composite dependency provider."""
    return AgentService(
        db_session=db_session,
        storage=storage_service,
        rate_limiter=rate_limiter,
    )
```

### 4. Error Handling in Dependencies

```python
# Dependency with error handling
async def provide_external_api_client() -> APIClient:
    """Provide API client with connection error handling."""
    try:
        client = APIClient(settings.api.BASE_URL)
        await client.ping()
        return client
    except ConnectionError:
        raise ServiceUnavailableException("External API is not reachable")
```

### 5. Caching Strategies

```python
# Cached dependency with TTL
@ttl_cache(maxsize=100, ttl=300)  # 5 minutes TTL
def provide_configuration_value(key: str) -> str:
    """Provide cached configuration value."""
    return settings.get_config_value(key)
```

## Performance Considerations

### Dependency Caching

- Use `@lru_cache` for expensive initialization operations
- Implement TTL caching for external service dependencies
- Cache database connection pools and expensive resources

### Lazy Loading

```python
# Lazy dependency loading
async def provide_heavy_service() -> HeavyService:
    """Lazy load expensive service."""
    if not _heavy_service_instance:
        _heavy_service_instance = await HeavyService.create()
    return _heavy_service_instance
```

### Resource Cleanup

```python
# Dependency cleanup
async def cleanup_dependencies(app_state: AppState) -> None:
    """Clean up application-level dependencies."""
    if hasattr(app_state, 'expensive_resource'):
        await app_state.expensive_resource.close()
```

## Troubleshooting Common Issues

### Circular Dependencies

```python
# Avoid circular dependencies with interface extraction
class ServiceA:
    def __init__(self, service_b: ServiceBInterface):
        self.service_b = service_b

class ServiceB:
    def __init__(self, service_a: ServiceAInterface):
        self.service_a = service_a
```

### Async Dependency Injection

```python
# Proper async dependency handling
async def provide_async_service() -> AsyncService:
    service = AsyncService()
    await service.initialize()
    return service
```

### Type Safety

```python
# Ensure type safety with TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services import SomeService

async def provide_service() -> SomeService:
    # Implementation
    pass
```

## Conclusion

This dependency injection system provides:

1. **Type Safety**: Full type annotation support
2. **Testability**: Easy mocking and overriding for tests
3. **Performance**: Efficient dependency caching and lazy loading
4. **Modularity**: Clean separation of concerns
5. **Scalability**: Support for complex dependency graphs
6. **Maintainability**: Clear dependency contracts and interfaces

The system leverages Litestar's native DI capabilities enhanced with custom patterns for database access, authentication, configuration, and domain-specific services. This creates a robust, maintainable, and highly testable application architecture.