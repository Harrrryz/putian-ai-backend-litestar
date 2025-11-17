# Domain-Driven Design Implementation

This document describes the Domain-Driven Design (DDD) patterns and implementation used throughout this Litestar application. The codebase follows DDD principles to create a well-structured, maintainable, and scalable system with clear separation of concerns.

## Table of Contents

1. [DDD Implementation Patterns](#ddd-implementation-patterns)
2. [Domain Structure and Bounded Contexts](#domain-structure-and-bounded-contexts)
3. [Domain Models, Entities, and Value Objects](#domain-models-entities-and-value-objects)
4. [Domain Services and Repositories](#domain-services-and-repositories)
5. [Application Services vs Domain Services](#application-services-vs-domain-services)
6. [Domain Events and Signaling](#domain-events-and-signaling)
7. [Aggregates and Aggregate Roots](#aggregates-and-aggregate-roots)
8. [Anti-corruption Layers and Integration Patterns](#anti-corruption-layers-and-integration-patterns)

## DDD Implementation Patterns

### Repository Pattern with Advanced Alchemy

The application uses Advanced Alchemy's repository pattern to implement data access with DDD principles:

```python
# Repository pattern implementation
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Handles database operations for users."""

    class UserRepository(SQLAlchemyAsyncRepository[m.User]):
        """User SQLAlchemy Repository."""
        model_type = m.User

    repository_type = UserRepository
    match_fields = ["email"]
```

### Service Layer Architecture

Each domain follows the service layer pattern with clear separation between application services (controllers) and domain services:

```python
# Domain Service
class TodoService(SQLAlchemyAsyncRepositoryService[m.Todo]):
    """Handles database operations for todo."""

    class Repository(SQLAlchemyAsyncRepository[m.Todo]):
        """Todo SQLAlchemy Repository."""
        model_type = m.Todo

    repository_type = Repository

    # Domain-specific business logic
    async def check_time_conflict(self, user_id: UUID, start_time: datetime, end_time: datetime) -> list[m.Todo]:
        # Business logic for checking time conflicts
        filters = [
            m.Todo.user_id == user_id,
            m.Todo.start_time < end_time,
            m.Todo.end_time > start_time,
        ]
        conflicts, _ = await self.list_and_count(*filters)
        return list(conflicts)
```

### Domain-Driven Configuration

The application core configuration demonstrates DDD principles by organizing services and controllers by domain:

```python
# src/app/server/core.py - Domain-driven service registration
app_config.signature_namespace.update({
    "UserService": UserService,
    "TodoService": TodoService,
    "TagService": TagService,
    "TodoAgentService": TodoAgentService,
    "UserUsageQuotaService": UserUsageQuotaService,
})

# Route registration by domain
app_config.route_handlers.extend([
    UserController,        # accounts domain
    TodoController,        # todo domain
    TodoAgentController,   # todo_agents domain
    SystemController,      # system domain
])
```

## Domain Structure and Bounded Contexts

The application is organized into distinct bounded contexts, each representing a specific business domain:

### Accounts Domain (`src/app/domain/accounts/`)
**Bounded Context**: User management, authentication, and authorization

**Responsibilities**:
- User registration, authentication, and authorization
- Role-based access control (RBAC)
- Email verification and password reset
- OAuth integration

**Key Components**:
- **Entities**: `User`, `Role`, `UserRole`, `UserOAuthAccount`
- **Services**: `UserService`, `RoleService`, `UserRoleService`
- **Controllers**: `UserController`, `AccessController`, `UserRoleController`
- **Value Objects**: Email addresses, verification tokens
- **Domain Events**: `user_created`

```python
# User aggregate root
class User(UUIDAuditBase):
    """User aggregate root with encapsulated business logic."""

    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Aggregate relationships
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete"
    )
    todos: Mapped[list[Todo]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    @hybrid_property
    def has_password(self) -> bool:
        """Domain logic: Check if user has password set."""
        return self.hashed_password is not None
```

### Todo Domain (`src/app/domain/todo/`)
**Bounded Context**: Todo item management and scheduling

**Responsibilities**:
- CRUD operations for todo items
- Time-based scheduling and conflict detection
- Tag management and categorization
- Todo importance levels

**Key Components**:
- **Entities**: `Todo`, `Tag`, `TodoTag`
- **Value Objects**: `Importance` enum, time ranges
- **Services**: `TodoService`, `TagService`
- **Controllers**: `TodoController`

```python
# Todo entity with business logic
class Todo(UUIDAuditBase):
    """Todo item entity with scheduling constraints."""

    item: Mapped[str] = mapped_column(String(length=100), index=True, nullable=False)
    importance: Mapped[Importance] = mapped_column(
        Enum(Importance, name="importance_enum"),
        nullable=False,
        default=Importance.NONE
    )

    # Association proxy for many-to-many relationship
    tags: AssociationProxy[list[Tag]] = association_proxy("todo_tags", "tag")

    # Aggregate root reference
    user: Mapped[User] = relationship(
        back_populates="todos", lazy="joined", uselist=False, innerjoin=True
    )
```

### Todo Agents Domain (`src/app/domain/todo_agents/`)
**Bounded Context**: AI-powered todo management

**Responsibilities**:
- Natural language processing for todo operations
- Agent tool integration and orchestration
- Conversation management and session persistence
- Integration with external AI services

**Key Components**:
- **Services**: `TodoAgentService`
- **Tools**: `UniversalTools`, `AgentFactory`
- **Controllers**: `TodoAgentController`
- **Value Objects**: Agent contexts, tool definitions

```python
# Domain service with external integration
class TodoAgentService:
    """Service class for managing todo agent interactions."""

    def __init__(self, todo_service: TodoService, tag_service: TagService,
                 rate_limit_service: RateLimitService, quota_service: UserUsageQuotaService):
        # Dependency injection of other domain services
        self.todo_service = todo_service
        self.tag_service = tag_service

    async def chat_with_agent(self, user_id: str, message: str) -> str:
        # Domain logic for agent interaction with business rules
        # Rate limiting and quota enforcement
        try:
            await self.rate_limit_service.check_and_increment_usage(UUID(user_id), self.quota_service)
        except RateLimitExceededException as e:
            return f"You have exceeded your monthly usage limit. {e.detail}"
```

### Agent Sessions Domain (`src/app/domain/agent_sessions/`)
**Bounded Context**: Session management for AI interactions

**Responsibilities**:
- Session persistence and management
- Message history tracking
- Session lifecycle management

### Quota Domain (`src/app/domain/quota/`)
**Bounded Context**: Usage quota and rate limiting

**Responsibilities**:
- Monthly usage quota tracking
- Rate limiting enforcement
- Usage analytics and reporting

### System Domain (`src/app/domain/system/`)
**Bounded Context**: System-level operations

**Responsibilities**:
- Health checks and monitoring
- System information
- Cross-cutting concerns

## Domain Models, Entities, and Value Objects

### Entities

Entities are objects with distinct identities that run through a lifecycle and can have different states.

```python
# User entity with identity and lifecycle
class User(UUIDAuditBase):
    """User entity with distinct identity and lifecycle."""

    # Identity is defined by UUID from base class
    email: Mapped[str] = mapped_column(unique=True, index=True)  # Business identifier

    # Entity state
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    # Entity behavior
    @hybrid_property
    def has_password(self) -> bool:
        """Entity behavior: Check password existence."""
        return self.hashed_password is not None
```

### Value Objects

Value objects are defined by their attributes rather than identity. In this codebase, enums and simple types serve as value objects.

```python
# Value object: Importance enumeration
class Importance(str, Enum):
    """Value object representing todo importance levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Used in entity
class Todo(UUIDAuditBase):
    importance: Mapped[Importance] = mapped_column(
        Enum(Importance, name="importance_enum"),
        nullable=False,
        default=Importance.NONE
    )
```

### Rich Domain Models

Domain models encapsulate business logic and maintain invariants:

```python
class TodoService(SQLAlchemyAsyncRepositoryService[m.Todo]):
    """Service with rich domain logic."""

    async def get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> m.Todo | None:
        """Domain operation: Get todo with authorization check."""
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
        """Domain rule: Check for scheduling conflicts."""
        filters = [
            m.Todo.user_id == user_id,        # Business rule: User-scoped
            m.Todo.start_time < end_time,     # Overlap condition 1
            m.Todo.end_time > start_time,     # Overlap condition 2
        ]

        if exclude_todo_id:
            filters.append(m.Todo.id != exclude_todo_id)

        conflicts, _ = await self.list_and_count(*filters)
        return list(conflicts)
```

## Domain Services and Repositories

### Repository Pattern Implementation

Repositories abstract data access and implement domain-specific query logic:

```python
class TagService(SQLAlchemyAsyncRepositoryService[m.Tag]):
    """Domain service with repository pattern."""

    class TagRepository(SQLAlchemyAsyncRepository[m.Tag]):
        """Tag repository with domain-specific queries."""
        model_type = m.Tag

    repository_type = TagRepository
    match_fields = ["name"]

    async def get_or_create_tag(self, user_id: UUID, name: str, color: str | None = None) -> m.Tag:
        """Domain operation: Get existing tag or create new one."""
        existing_tag = await self.get_one_or_none(
            m.Tag.user_id == user_id,
            m.Tag.name == name
        )

        if existing_tag:
            return existing_tag

        return await self.create({
            "name": name,
            "color": color,
            "user_id": user_id
        })
```

### Service Layer Responsibilities

Domain services encapsulate business logic that doesn't naturally fit within entities:

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Domain service for user business operations."""

    async def authenticate(self, username: str, password: bytes | str) -> m.User:
        """Domain operation: Authenticate user with business rules."""
        db_obj = await self.get_one_or_none(email=username)
        if db_obj is None:
            msg = "User not found or password invalid"
            raise PermissionDeniedException(detail=msg)

        if not db_obj.is_active:
            msg = "User account is inactive"
            raise PermissionDeniedException(detail=msg)

        if not db_obj.is_verified:
            msg = "User account is not verified"
            raise PermissionDeniedException(detail=msg)

        if not await crypt.verify_password(password, db_obj.hashed_password):
            msg = "User not found or password invalid"
            raise PermissionDeniedException(detail=msg)

        return db_obj

    @staticmethod
    def is_superuser(user: m.User) -> bool:
        """Domain rule: Superuser determination."""
        return bool(
            user.is_superuser or
            any(assigned_role.role.name for assigned_role in user.roles
                if assigned_role.role.name in {"Superuser"})
        )
```

## Application Services vs Domain Services

### Application Services (Controllers)

Application services coordinate use cases and orchestrate domain objects. They are thin and focus on application flow:

```python
class UserController(Controller):
    """Application service: HTTP endpoint coordination."""

    @post(operation_id="CreateUser", path=urls.ACCOUNT_CREATE)
    async def create_user(self, users_service: UserService, data: UserCreate) -> User:
        """Application service: User creation use case."""
        # Delegate to domain service
        db_obj = await users_service.create(data.to_dict())
        # Convert to DTO
        return users_service.to_schema(db_obj, schema_type=User)

    @get(operation_id="GetUser", path=urls.ACCOUNT_DETAIL)
    async def get_user(self, users_service: UserService, user_id: UUID) -> User:
        """Application service: User retrieval use case."""
        # Delegate to domain service
        db_obj = await users_service.get(user_id)
        # Convert to DTO
        return users_service.to_schema(db_obj, schema_type=User)
```

### Domain Services

Domain services contain business logic and domain rules:

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Domain service: User business logic."""

    async def _populate_with_hashed_password(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
        """Domain logic: Password hashing transformation."""
        if is_dict(data) and (password := data.pop("password", None)) is not None:
            data["hashed_password"] = await crypt.get_password_hash(password)
        return data

    async def send_verification_email(self, user: m.User, verification_token: str) -> bool:
        """Domain operation: Email sending with business context."""
        return await send_verification_email(
            smtp_settings=settings.smtp,
            to_email=user.email,
            user_name=user.name,
            verification_token=verification_token,
            base_url="http://localhost:8081",
        )
```

## Domain Events and Signaling

### Event-Driven Architecture

The application implements domain events for loose coupling and reactive behavior:

```python
# src/app/domain/accounts/signals.py
@listener("user_created")
async def user_created_event_handler(user_id: UUID) -> None:
    """Domain event handler for user creation."""
    await logger.ainfo("Running post signup flow.")
    async with alchemy.get_session() as db_session:
        service = await anext(provide_users_service(db_session))
        obj = await service.get_one_or_none(id=user_id)
        if obj is None:
            await logger.aerror("Could not locate the specified user", id=user_id)
        else:
            await logger.ainfo("Found user", **obj.to_dict(exclude={"hashed_password"}))
```

### Event Registration in Application Core

```python
# src/app/server/core.py
def on_app_init(self, app_config: AppConfig) -> AppConfig:
    # ...
    # Domain event listeners
    app_config.listeners.extend([
        account_signals.user_created_event_handler,
    ])
    return app_config
```

### Domain Events in Service Layer

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    async def verify_user_email(self, user_id: UUID) -> m.User:
        """Domain operation with side effects and potential events."""
        user = await self.get_one(id=user_id)

        # Update user verification status
        await self.update(item_id=user_id, data={
            "is_verified": True,
            "verified_at": datetime.now(UTC).date(),
        })

        # Side effect: Send welcome email
        verified_user = await self.get_one(id=user_id)
        try:
            await self.send_welcome_email(verified_user)
        except Exception:
            # Log error but don't fail the verification process
            pass

        return verified_user
```

## Aggregates and Aggregate Roots

### User Aggregate

The User aggregate manages user-related entities and enforces consistency boundaries:

```python
class User(UUIDAuditBase):
    """User aggregate root."""

    # Aggregate root properties
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Aggregate members (cascading delete ensures consistency)
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete"  # Maintain aggregate consistency
    )

    todos: Mapped[list[Todo]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"  # Maintain aggregate consistency
    )

    tags: Mapped[list[Tag]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # Aggregate invariants and business rules
    @hybrid_property
    def has_password(self) -> bool:
        """Aggregate invariant: Password requirement check."""
        return self.hashed_password is not None
```

### Todo Aggregate

The Todo aggregate represents the scheduling domain:

```python
class Todo(UUIDAuditBase):
    """Todo aggregate root."""

    # Aggregate root identity and state
    item: Mapped[str] = mapped_column(String(length=100), index=True, nullable=False)
    importance: Mapped[Importance] = mapped_column(Enum(Importance), nullable=False)

    # Aggregate relationships
    todo_tags: Mapped[list[TodoTag]] = relationship(
        back_populates="todo",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    tags: AssociationProxy[list[Tag]] = association_proxy("todo_tags", "tag")

    # Aggregate root reference (for consistency checks)
    user: Mapped[User] = relationship(
        back_populates="todos",
        lazy="joined",
        uselist=False,
        innerjoin=True
    )
```

### Aggregate Consistency Enforcement

```python
class TodoService(SQLAlchemyAsyncRepositoryService[m.Todo]):
    """Service enforcing aggregate consistency."""

    async def check_time_conflict(
        self,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_todo_id: UUID | None = None
    ) -> list[m.Todo]:
        """Enforce aggregate invariant: No time conflicts within user aggregate."""
        filters = [
            m.Todo.user_id == user_id,  # Aggregate boundary
            m.Todo.start_time < end_time,
            m.Todo.end_time > start_time,
        ]

        if exclude_todo_id:
            filters.append(m.Todo.id != exclude_todo_id)

        conflicts, _ = await self.list_and_count(*filters)
        return list(conflicts)
```

## Anti-corruption Layers and Integration Patterns

### External Service Integration

The application implements anti-corruption layers when integrating with external services:

```python
class TodoAgentService:
    """Anti-corruption layer for AI agent integration."""

    def __init__(self, todo_service: TodoService, tag_service: TagService,
                 rate_limit_service: RateLimitService, quota_service: UserUsageQuotaService):
        self.todo_service = todo_service
        self.tag_service = tag_service
        self.rate_limit_service = rate_limit_service
        self.quota_service = quota_service

    async def chat_with_agent(self, user_id: str, message: str) -> str:
        """Anti-corruption: Translate external AI service to domain model."""
        # Pre-condition checks (domain rules)
        try:
            await self.rate_limit_service.check_and_increment_usage(
                UUID(user_id), self.quota_service
            )
        except RateLimitExceededException as e:
            # Translate domain exception to user-friendly message
            return f"You have exceeded your monthly usage limit. {e.detail}"

        # Set agent context (anti-corruption layer)
        set_agent_context(
            self.todo_service,
            self.tag_service,
            UUID(user_id),
            quota_service=self.quota_service,
            rate_limit_service=self.rate_limit_service,
        )

        # External service interaction
        agent = get_todo_agent()
        result = await Runner.run(agent, message, max_turns=20)

        # Return domain-friendly response
        return result.final_output
```

### Email Service Integration

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Anti-corruption layer for email service integration."""

    async def send_verification_email(self, user: m.User, verification_token: str) -> bool:
        """Translate domain email needs to external SMTP service."""
        return await send_verification_email(
            smtp_settings=settings.smtp,  # External service configuration
            to_email=user.email,
            user_name=user.name,
            verification_token=verification_token,
            base_url="http://localhost:8081",
        )
```

### Database Integration Layer

The application uses Advanced Alchemy as an anti-corruption layer between domain models and database:

```python
# Repository as anti-corruption layer
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Anti-corruption layer for database operations."""

    async def to_model_on_create(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
        """Transform input to domain model."""
        return await self._populate_model(data)

    async def _populate_with_hashed_password(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
        """Domain logic: Handle password hashing before persistence."""
        if is_dict(data) and (password := data.pop("password", None)) is not None:
            data["hashed_password"] = await crypt.get_password_hash(password)
        return data
```

### Configuration Anti-corruption

```python
# Domain-specific configuration
class UserUsageQuotaService(SQLAlchemyAsyncRepositoryService[m.UserUsageQuota]):
    """Anti-corruption layer for quota management."""

    async def get_or_create_quota(self, user_id: UUID, month_year: str) -> m.UserUsageQuota:
        """Encapsulate quota creation logic with business rules."""
        existing_quota = await self.get_one_or_none(
            m.UserUsageQuota.user_id == str(user_id),
            m.UserUsageQuota.month_year == month_year,
        )

        if existing_quota:
            return existing_quota

        return await self.create({
            "user_id": str(user_id),
            "month_year": month_year,
            "usage_count": 0,  # Business rule: Start at zero
        })
```

## Summary

This Domain-Driven Design implementation provides:

1. **Clear Bounded Contexts**: Each domain has well-defined responsibilities and boundaries
2. **Rich Domain Models**: Business logic is encapsulated in entities and domain services
3. **Repository Pattern**: Data access is abstracted with domain-specific repositories
4. **Service Layer Separation**: Clear distinction between application services and domain services
5. **Event-Driven Architecture**: Loose coupling through domain events
6. **Aggregate Consistency**: Proper aggregate design maintains consistency boundaries
7. **Anti-corruption Layers**: External integrations are properly isolated from the domain model

The implementation follows DDD principles while leveraging Python's type system, SQLAlchemy's ORM capabilities, and Litestar's dependency injection to create a maintainable and scalable architecture.