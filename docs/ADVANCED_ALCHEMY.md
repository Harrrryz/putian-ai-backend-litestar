# Advanced Alchemy Integration

This document provides comprehensive documentation for Advanced Alchemy integration within the Litestar Todo application. Advanced Alchemy serves as the foundation for database operations, providing a robust SQLAlchemy integration with enhanced repository patterns and service layers.

## Overview

Advanced Alchemy is a library that extends SQLAlchemy with additional functionality including:
- Repository pattern implementation
- Service layer abstraction
- Enhanced base models with audit fields
- Type-safe database operations
- Integration with Litestar framework
- Migration management with Alembic

## 1. Setup and Configuration

### 1.1 Dependencies

The application uses Advanced Alchemy with UUID support:

```toml
# pyproject.toml
dependencies = [
    "advanced-alchemy[uuid]>=0.33.2",
    # ... other dependencies
]

# Testing dependencies
test = [
    "pytest-databases[postgres]>=0.1.0",
    # ... other test dependencies
]
```

### 1.2 Database Configuration

Advanced Alchemy is configured through the `SQLAlchemyAsyncConfig` in `src/app/config/app.py`:

```python
from litestar.plugins.sqlalchemy import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
)

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

### 1.3 Plugin Registration

The Advanced Alchemy plugin is registered in `src/app/server/plugins.py`:

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin

alchemy = SQLAlchemyPlugin(config=config.alchemy)
```

And loaded in the application core configuration:

```python
# src/app/server/core.py
app_config.plugins.extend([
    # ... other plugins
    plugins.alchemy,
    # ... other plugins
])
```

### 1.4 Database Engine Configuration

The database engine is configured in `src/app/config/base.py` with support for both PostgreSQL and SQLite:

```python
@dataclass
class DatabaseSettings:
    URL: str = field(default_factory=get_env(
        "DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3"))

    # Connection pool settings for PostgreSQL
    POOL_MAX_OVERFLOW: int = field(default_factory=get_env("DATABASE_MAX_POOL_OVERFLOW", 10))
    POOL_SIZE: int = field(default_factory=get_env("DATABASE_POOL_SIZE", 5))
    POOL_TIMEOUT: int = field(default_factory=get_env("DATABASE_POOL_TIMEOUT", 30))
    POOL_RECYCLE: int = field(default_factory=get_env("DATABASE_POOL_RECYCLE", 300))

    def get_engine(self) -> AsyncEngine:
        if self.URL.startswith("postgresql+asyncpg"):
            engine = create_async_engine(
                url=self.URL,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=self.ECHO,
                max_overflow=self.POOL_MAX_OVERFLOW,
                pool_size=self.POOL_SIZE,
                pool_timeout=self.POOL_TIMEOUT,
                pool_recycle=self.POOL_RECYCLE,
                pool_use_lifo=True,
                # Additional PostgreSQL-specific configuration
            )
            # PostgreSQL codec configuration for JSON/JSONB
            # ...
        elif self.URL.startswith("sqlite+aiosqlite"):
            engine = create_async_engine(
                url=self.URL,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=self.ECHO,
                pool_recycle=self.POOL_RECYCLE,
            )
            # SQLite-specific configuration
            # ...

        return engine
```

## 2. Repository Pattern Implementation

### 2.1 Base Repository Classes

Advanced Alchemy provides base repository classes that implement common CRUD operations:

```python
from advanced_alchemy.repository import (
    SQLAlchemyAsyncRepository,
    SQLAlchemyAsyncSlugRepository,
)

# Standard repository
class UserRepository(SQLAlchemyAsyncRepository[m.User]):
    model_type = m.User

# Slug-based repository (for entities with slugs)
class RoleRepository(SQLAlchemyAsyncSlugRepository[m.Role]):
    model_type = m.Role
```

### 2.2 Custom Repository Methods

Repositories can be extended with custom query methods:

```python
# src/app/domain/todo/services.py
class TodoService(SQLAlchemyAsyncRepositoryService[m.Todo]):
    class Repository(SQLAlchemyAsyncRepository[m.Todo]):
        model_type = m.Todo

    async def get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> m.Todo | None:
        """Get a todo item by ID for the specified user."""
        todo = await self.get_one_or_none(
            m.Todo.id == todo_id,
            m.Todo.user_id == user_id
        )
        return todo

    async def check_time_conflict(
        self,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_todo_id: UUID | None = None
    ) -> list[m.Todo]:
        """Check for time conflicts with existing todos for a user."""
        filters = [
            m.Todo.user_id == user_id,
            m.Todo.start_time < end_time,
            m.Todo.end_time > start_time,
        ]

        if exclude_todo_id:
            filters.append(m.Todo.id != exclude_todo_id)

        conflicts, _ = await self.list_and_count(*filters)
        return list(conflicts)
```

### 2.3 Repository Usage Patterns

Repositories are typically used through service classes:

```python
# In a service or controller
async def get_user_todos(user_id: UUID) -> list[m.Todo]:
    todo_service = TodoService()
    todos, _ = await todo_service.list_and_count(m.Todo.user_id == user_id)
    return list(todos)
```

## 3. Model Definitions and SQLAlchemy Integration

### 3.1 Base Classes

Models use Advanced Alchemy base classes for enhanced functionality:

```python
from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.mixins import SlugKey

# Standard audit model with UUID primary key
class User(UUIDAuditBase):
    __tablename__ = "user_account"
    __table_args__ = {"comment": "User accounts for application access"}
    __pii_columns__ = {"name", "email", "avatar_url"}  # PII column tracking

# Model with slug support
class Role(UUIDAuditBase, SlugKey):
    __tablename__ = "role"
    __table_args__ = {"comment": "User roles"}
```

### 3.2 Model Field Definitions

Models use SQLAlchemy 2.0 style field definitions:

```python
from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy

class Todo(UUIDAuditBase):
    __tablename__ = "todo"
    __table_args__ = {"comment": "Todo items"}
    __pii_columns__ = {"item", "created_time", "alarm_time", "content", "user", "importance", "tags"}

    # Basic fields
    item: Mapped[str] = mapped_column(String(length=100), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(length=1024), nullable=True)

    # Enum field
    importance: Mapped[Importance] = mapped_column(
        Enum(Importance, name="importance_enum", native_enum=False),
        nullable=False,
        default=Importance.NONE
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False
    )

    # DateTime fields
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=False)
```

### 3.3 Relationships and Association Proxies

Advanced Alchemy models support complex relationships:

```python
class User(UUIDAuditBase):
    # One-to-many relationships
    todos: Mapped[list[Todo]] = relationship(
        back_populates="user",
        lazy="selectin",  # Efficient loading strategy
        uselist=True,
        cascade="all, delete-orphan",
    )

    # Many-to-many through association table
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        lazy="selectin",
        uselist=True,
        cascade="all, delete",
    )

class UserRole(UUIDAuditBase):
    user: Mapped[User] = relationship(
        back_populates="roles",
        innerjoin=True,
        uselist=False,
        lazy="joined"
    )

    # Association proxies for convenient access
    user_name: AssociationProxy[str] = association_proxy("user", "name")
    user_email: AssociationProxy[str] = association_proxy("user", "email")
    role_name: AssociationProxy[str] = association_proxy("role", "name")
```

### 3.4 Audit Fields

`UUIDAuditBase` automatically provides these fields:
- `id`: UUID primary key
- `created_at`: Creation timestamp with timezone
- `updated_at`: Last modification timestamp with timezone
- `sa_orm_sentinel`: Internal SQLAlchemy field

## 4. Database Session Management and Transactions

### 4.1 Session Configuration

Sessions are configured with `AsyncSessionConfig`:

```python
session_config=AsyncSessionConfig(expire_on_commit=False)
```

### 4.2 Transaction Management

Advanced Alchemy provides automatic transaction management:

```python
# Automatic transaction handling
async def create_todo(data: dict[str, Any]) -> m.Todo:
    service = TodoService()
    return await service.create(data)

# Manual transaction control (if needed)
async def complex_operation():
    async with service.repository.session.begin():
        # Multiple operations in a single transaction
        todo = await service.create(todo_data)
        tag = await tag_service.create(tag_data)
        # All operations will be committed or rolled back together
```

### 4.3 Session Lifecycle

Sessions are managed automatically by the Litestar plugin:
- Created per request
- Automatically committed or rolled back
- Properly closed after request completion

## 5. Query Building and Optimization

### 5.1 Basic Queries

```python
# Find single record
user = await user_service.get_one(email="user@example.com")

# Find or return None
user = await user_service.get_one_or_none(email="user@example.com")

# List with filters
todos, count = await todo_service.list_and_count(
    m.Todo.user_id == user_id,
    m.Todo.importance == Importance.HIGH
)
```

### 5.2 Advanced Query Patterns

```python
# Complex filtering with multiple conditions
async def get_active_todos_by_importance(user_id: UUID, importance: Importance):
    filters = [
        m.Todo.user_id == user_id,
        m.Todo.importance == importance,
        m.Todo.start_time <= datetime.now(UTC),
        m.Todo.end_time >= datetime.now(UTC),
    ]

    todos, _ = await todo_service.list_and_count(*filters)
    return list(todos)

# Pagination
async def get_todos_paginated(user_id: UUID, page: int, size: int):
    todos, total = await todo_service.list_and_count(
        m.Todo.user_id == user_id,
        limit=size,
        offset=(page - 1) * size
    )

    return {
        "items": list(todos),
        "total": total,
        "page": page,
        "size": size
    }
```

### 5.3 Query Optimization

```python
# Efficient loading strategies
class User(UUIDAuditBase):
    # Use selectin for collections (good for many-to-many)
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    # Use joined for single related objects
    profile: Mapped[UserProfile] = relationship(
        back_populates="user",
        lazy="joined",
    )

    # Use noload for relationships you won't need
    audit_logs: Mapped[list[AuditLog]] = relationship(
        lazy="noload",
    )

# Custom queries with joins
async def get_todos_with_tags(user_id: UUID):
    result = await todo_service.repository.session.execute(
        select(m.Todo)
        .options(selectinload(m.Todo.tags))
        .where(m.Todo.user_id == user_id)
    )
    return result.scalars().all()
```

## 6. Migration Management Integration

### 6.1 Alembic Configuration

Advanced Alchemy integrates with Alembic for migrations:

```python
# src/app/db/migrations/env.py
from advanced_alchemy.base import orm_registry

# Use Advanced Alchemy's registry
target_metadata = orm_registry.metadata

# Async migration support
async def run_migrations_online() -> None:
    connectable = cast(
        "AsyncEngine",
        config.engine
        or async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        ),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
```

### 6.2 Migration Structure

Migrations use Advanced Alchemy types and patterns:

```python
# Migration file example
import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC

# Type mapping for migrations
sa.GUID = GUID
sa.DateTimeUTC = DateTimeUTC

def schema_upgrades() -> None:
    op.create_table('user_account',
        sa.Column('id', sa.GUID(length=16), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTimeUTC(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_account'))
    )

    with op.batch_alter_table('user_account', schema=None) as batch_op:
        batch_op.create_index(op.f('ix_user_account_email'), ['email'], unique=True)
```

### 6.3 Migration Commands

```bash
# Create new migration
uv run app database make-migrations

# Run migrations
uv run app database upgrade

# Rollback migrations
uv run app database downgrade
```

## 7. Testing with Advanced Alchemy

### 7.1 Test Configuration

Tests use pytest-databases for isolated database testing:

```python
# tests/conftest.py
pytest_plugins = [
    "tests.data_fixtures",
    "pytest_databases.docker",
    "pytest_databases.docker.postgres",
]

@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: MonkeyPatch) -> None:
    settings = base.Settings.from_env(".env.testing")
    monkeypatch.setattr(base, "get_settings", lambda: settings)
```

### 7.2 Test Fixtures

```python
# tests/data_fixtures.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def user_service(db_session: AsyncSession) -> UserService:
    return UserService(session=db_session)

@pytest.fixture
async def todo_service(db_session: AsyncSession) -> TodoService:
    return TodoService(session=db_session)
```

### 7.3 Service Testing

```python
# tests/unit/test_services.py
async def test_create_user(user_service: UserService):
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "securepassword"
    }

    user = await user_service.create(user_data)

    assert user.email == user_data["email"]
    assert user.name == user_data["name"]
    assert user.hashed_password is not None
    assert user.id is not None

async def test_user_authentication(user_service: UserService):
    # Create user first
    user = await user_service.create({
        "email": "auth@example.com",
        "password": "password123"
    })

    # Test authentication
    authenticated_user = await user_service.authenticate(
        "auth@example.com",
        "password123"
    )

    assert authenticated_user.id == user.id
```

### 7.4 Integration Testing

```python
# tests/integration/test_todos.py
async def test_create_todo_with_tags(todo_service: TodoService, tag_service: TagService):
    # Create tag
    tag = await tag_service.create({
        "name": "work",
        "user_id": user_id
    })

    # Create todo with tag
    todo = await todo_service.create({
        "item": "Complete project",
        "user_id": user_id,
        "start_time": datetime.now(UTC),
        "end_time": datetime.now(UTC) + timedelta(hours=2)
    })

    # Add tag to todo
    todo_tag = await todo_tag_service.create({
        "todo_id": todo.id,
        "tag_id": tag.id
    })

    # Verify todo has tag
    loaded_todo = await todo_service.get_todo_by_id(todo.id, user_id)
    assert len(loaded_todo.tags) == 1
    assert loaded_todo.tags[0].name == "work"
```

## 8. Performance Considerations and Best Practices

### 8.1 Query Optimization

```python
# DO: Use efficient loading strategies
todos, _ = await todo_service.list_and_count(
    m.Todo.user_id == user_id,
    # Specify loading strategy in relationship definition
)

# AVOID: N+1 queries
for todo in todos:
    print(todo.user.name)  # This triggers separate queries

# DO: Use selectinload for collections
from sqlalchemy.orm import selectinload

todos = await todo_service.list(
    select(m.Todo).options(selectinload(m.Todo.tags))
)
```

### 8.2 Connection Pool Management

```python
# Configure appropriate pool settings
POOL_SIZE = 5  # Base connections
POOL_MAX_OVERFLOW = 10  # Additional connections under load
POOL_TIMEOUT = 30  # Wait time for connection
POOL_RECYCLE = 300  # Connection lifetime in seconds
POOL_PRE_PING = True  # Validate connections before use
```

### 8.3 Bulk Operations

```python
# Use bulk operations for multiple records
async def create_multiple_todos(todo_data_list: list[dict]):
    service = TodoService()
    return await service.repository.bulk_create(todo_data_list)

# Bulk updates
async def update_todos_importance(todo_ids: list[UUID], importance: Importance):
    service = TodoService()
    return await service.repository.bulk_update(
        todo_ids, {"importance": importance}
    )
```

### 8.4 Indexing Strategy

```python
# Add indexes for frequently queried fields
class Todo(UUIDAuditBase):
    item: Mapped[str] = mapped_column(String(length=100), index=True)  # Single column index

    # Composite index for common query patterns
    __table_args__ = (
        Index("ix_todo_user_importance", "user_id", "importance"),
        Index("ix_todo_time_range", "start_time", "end_time"),
    )
```

### 8.5 Caching Strategies

```python
# Use Litestar's built-in caching
from litestar import Controller, get
from litestar.response import Response

class TodoController(Controller):
    path = "/todos"

    @get("/{todo_id:int}", cache=60)  # Cache for 60 seconds
    async def get_todo(self, todo_id: int) -> Response[m.Todo]:
        todo = await self.todo_service.get(todo_id)
        return Response(todo)
```

### 8.6 Error Handling

```python
# Handle Advanced Alchemy exceptions
from advanced_alchemy.exceptions import RepositoryError

async def safe_create_todo(data: dict[str, Any]):
    try:
        return await todo_service.create(data)
    except RepositoryError as exc:
        # Log the error
        logger.error(f"Database error creating todo: {exc}")
        # Convert to application error
        raise ApplicationError("Could not create todo") from exc
```

### 8.7 Monitoring and Logging

```python
# Enable query logging in development
DATABASE_ECHO = True  # Log all SQL queries
DATABASE_ECHO_POOL = True  # Log connection pool activity

# Production logging configuration
LOGGING_CONFIG = {
    "loggers": {
        "sqlalchemy.engine": {
            "level": "WARNING",  # Reduce noise in production
            "handlers": ["console"],
        },
        "sqlalchemy.pool": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
}
```

## 9. Advanced Features

### 9.1 Encrypted Fields

Advanced Alchemy provides encrypted field types:

```python
from advanced_alchemy.types import EncryptedString, EncryptedText

class User(UUIDAuditBase):
    # Encrypted sensitive data
    ssn: Mapped[str] = mapped_column(
        EncryptedString(max_length=11), nullable=True
    )

    notes: Mapped[str] = mapped_column(
        EncryptedText, nullable=True
    )
```

### 9.2 Soft Deletes

```python
# Implement soft deletes with Advanced Alchemy
class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)

class Todo(UUIDAuditBase, SoftDeleteMixin):
    # Add filter for soft deletes in queries
    @classmethod
    def get_active_filter(cls):
        return cls.is_deleted == False
```

### 9.3 Custom Types

```python
from sqlalchemy import TypeDecorator, JSON
from uuid import UUID

class UUIDArray(TypeDecorator):
    """Custom type for storing UUID arrays"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if value is not None:
            return [str(u) for u in value]
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return [UUID(u) for u in value]
        return value

class Todo(UUIDAuditBase):
    related_todos: Mapped[list[UUID]] = mapped_column(UUIDArray, nullable=True)
```

## Conclusion

Advanced Alchemy provides a comprehensive solution for database operations in Litestar applications, offering:

1. **Type Safety**: Full type hints and runtime type checking
2. **Repository Pattern**: Clean separation of data access logic
3. **Service Layer**: Business logic abstraction
4. **Migration Support**: Integrated Alembic migrations
5. **Performance**: Optimized query patterns and connection management
6. **Testing**: Comprehensive testing utilities
7. **Security**: Encrypted fields and PII tracking
8. **Monitoring**: Built-in logging and error handling

By following the patterns and best practices outlined in this document, developers can build robust, scalable, and maintainable database layers for their Litestar applications using Advanced Alchemy.