# Application Structure & Organization

This document provides a comprehensive overview of the application's structure, organization, and architectural patterns used throughout the codebase.

## Table of Contents

- [Project Overview](#project-overview)
- [Directory Structure](#directory-structure)
- [Component Organization](#component-organization)
- [Domain-Driven Design](#domain-driven-design)
- [Configuration Management](#configuration-management)
- [Database Organization](#database-organization)
- [Testing Structure](#testing-structure)
- [Deployment Structure](#deployment-structure)
- [Package Dependencies](#package-dependencies)
- [Module Relationships](#module-relationships)
- [Naming Conventions](#naming-conventions)

## Project Overview

This is a modern Litestar-based web application following Domain-Driven Design (DDD) principles. The application provides AI-powered todo management with user authentication, role-based access control, and agent integration capabilities.

**Key Technologies:**
- **Framework**: Litestar with ASGI support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: OpenAI Agents with Volcengine Doubao model
- **Authentication**: JWT with OAuth2 social login support
- **Architecture**: Domain-Driven Design with clean architecture principles

## Directory Structure

```
putian-ai-todo-back-end-litestar/
├── src/                           # Source code directory
│   └── app/                       # Main application package
│       ├── __init__.py           # Package initialization with multiprocessing config
│       ├── __about__.py          # Application metadata and version info
│       ├── asgi.py               # ASGI application factory
│       ├── __main__.py           # CLI entry point
│       ├── cli/                  # Command-line interface modules
│       ├── config/               # Configuration management
│       ├── db/                   # Database layer (models, migrations)
│       ├── domain/               # Business logic domains
│       ├── lib/                  # Shared libraries and utilities
│       └── server/               # Server configuration and plugins
├── tests/                        # Test suite
│   ├── integration/              # Integration tests
│   ├── unit/                     # Unit tests
│   ├── conftest.py               # Pytest configuration
│   ├── data_fixtures.py          # Test data fixtures
│   └── helpers.py                # Test helper utilities
├── docs/                         # Documentation
├── deploy/                       # Deployment configurations
├── fixtures/                     # Database fixtures
├── examples/                     # Example code
├── notebooks/                    # Jupyter notebooks
├── pyproject.toml               # Project configuration and dependencies
├── Makefile                     # Development commands
├── docker-compose.yml           # Docker composition
├── docker-compose.override.yml  # Docker override configuration
├── uv.lock                      # Dependency lock file
└── CLAUDE.md                    # Claude Code development guide
```

## Component Organization

### 1. Application Core (`src/app/server/`)

The server component contains the main application configuration:

- **`core.py`**: Main application plugin that configures routes, dependencies, and middleware
- **`plugins/`**: Litestar plugin configurations (structlog, granian, alchemy, etc.)

**Key responsibilities:**
- Route registration and configuration
- Dependency injection setup
- Plugin initialization
- Exception handler configuration
- OpenAPI/Swagger documentation setup

### 2. Configuration Management (`src/app/config/`)

Hierarchical configuration system with environment-based settings:

- **`base.py`**: Core settings classes (DatabaseSettings, AppSettings, etc.)
- **`app.py`**: Application-specific configuration
- **`constants.py`**: Application constants and enums
- **`_utils.py`**: Configuration utility functions

**Configuration hierarchy:**
1. Base configuration with defaults
2. Environment-specific overrides
3. Runtime environment variable injection
4. Type validation and conversion

### 3. Database Layer (`src/app/db/`)

Comprehensive database organization:

```
src/app/db/
├── __init__.py                  # Database initialization
├── models/                      # SQLAlchemy model definitions
│   ├── user.py                  # User account model
│   ├── role.py                  # Role and permission models
│   ├── todo.py                  # Todo item model
│   ├── tag.py                   # Tag model
│   ├── agent_session.py         # AI agent session model
│   ├── session_message.py       # Agent message model
│   ├── oauth_account.py         # OAuth account linking
│   ├── email_verification_token.py  # Email verification tokens
│   ├── password_reset_token.py  # Password reset tokens
│   └── todo_tag.py              # Todo-tag relationships
├── migrations/                  # Alembic database migrations
│   ├── env.py                   # Migration environment setup
│   ├── script.py.mako           # Migration script template
│   └── versions/                # Versioned migration files
└── fixtures/                    # Database seed data
    └── role.json                # Default roles configuration
```

**Key features:**
- SQLAlchemy models with UUID primary keys
- Alembic for database migrations
- Async database operations
- Comprehensive relationship modeling
- Database fixtures for testing and development

### 4. Domain Layer (`src/app/domain/`)

Business logic organized by domain following DDD principles:

```
src/app/domain/
├── accounts/                    # User management domain
│   ├── controllers/             # HTTP route handlers
│   │   ├── access.py           # Authentication endpoints
│   │   ├── users.py            # User management endpoints
│   │   ├── roles.py            # Role management endpoints
│   │   └── user_role.py        # User-role assignment endpoints
│   ├── services.py              # Business logic services
│   ├── services_email_verification.py  # Email verification logic
│   ├── services_password_reset.py      # Password reset logic
│   ├── schemas.py               # Data transfer objects
│   ├── guards.py                # Authorization guards
│   ├── deps.py                  # Dependency injection providers
│   ├── signals.py               # Domain event handlers
│   └── urls.py                  # Route configuration
├── todo/                        # Todo management domain
│   ├── controllers/             # Todo endpoints
│   ├── services.py              # Todo business logic
│   └── schemas.py               # Todo data schemas
├── todo_agents/                 # AI agent integration domain
│   ├── controllers/             # Agent endpoints
│   ├── services.py              # Agent business logic
│   └── tools/                   # Agent function tools
├── agent_sessions/              # Agent session management
│   ├── controllers/             # Session endpoints
│   ├── services.py              # Session business logic
│   └── schemas.py               # Session data schemas
├── quota/                       # Usage quota management
│   └── services.py              # Quota enforcement logic
└── system/                      # System-level functionality
    ├── controllers/             # System endpoints
    └── schemas.py               # System data schemas
```

**Domain architecture principles:**
- Each domain is self-contained with its own controllers, services, and schemas
- Controllers handle HTTP requests and delegate to services
- Services contain business logic and orchestrate domain operations
- Schemas define data transfer objects for validation and serialization
- Cross-domain communication occurs through well-defined interfaces

### 5. Shared Libraries (`src/app/lib/`)

Common utilities and shared functionality:

```
src/app/lib/
├── __init__.py
├── crypt.py                     # Cryptographic utilities (password hashing)
├── database_session.py          # Database session management
├── deps.py                      # Shared dependency providers
├── dto.py                       # Base DTO classes
├── email.py                     # Email service integration
├── exceptions.py                # Custom exception definitions
├── oauth.py                     # OAuth integration utilities
├── rate_limit_service.py        # Rate limiting implementation
└── schema.py                    # Shared schema utilities
```

## Domain-Driven Design Patterns

### 1. Bounded Contexts

Each domain represents a bounded context with:
- **Ubiquitous Language**: Domain-specific terminology used throughout
- **Explicit Boundaries**: Clear separation between different business areas
- **Data Isolation**: Each domain manages its own data models and services

### 2. Service Layer Pattern

Services coordinate business logic and maintain transaction boundaries:

```python
# Service pattern example
class TodoService:
    def __init__(self, session: AsyncSession, repository: TodoRepository):
        self.session = session
        self.repository = repository

    async def create_todo(self, todo_data: TodoCreate) -> Todo:
        # Business logic implementation
        todo = await self.repository.create(todo_data)
        # Domain events, validation, etc.
        return todo
```

### 3. Repository Pattern

Data access abstraction through repositories:
- **Interface Definition**: Abstract repository interfaces
- **Implementation**: Concrete SQLAlchemy-based repositories
- **Testability**: Easy to mock for unit testing

### 4. Command Query Responsibility Segregation (CQRS)

Separation of read and write operations:
- **Commands**: Write operations (create, update, delete)
- **Queries**: Read operations (get, list, search)
- **Separation**: Different handlers for commands and queries

## Configuration Organization

### 1. Environment-Based Configuration

Configuration is loaded based on the `APP_ENV` environment variable:

```python
# Configuration loading hierarchy
base_config = load_base_config()
environment_config = load_environment_config(APP_ENV)
final_config = merge_configs(base_config, environment_config)
```

### 2. Settings Categories

- **DatabaseSettings**: Database connection and pool configuration
- **AppSettings**: Application-specific settings (name, debug, etc.)
- **SecuritySettings**: JWT, OAuth, and security-related settings
- **AISettings**: AI service integration settings
- **EmailSettings**: Email service configuration

### 3. Type Safety

All configuration is type-annotated with Pydantic for:
- **Validation**: Automatic validation of configuration values
- **Type Safety**: Compile-time type checking
- **Documentation**: Self-documenting configuration schema

## Database Organization

### 1. Migration Strategy

Alembic migrations with:
- **Automatic Generation**: `alembic revision --autogenerate`
- **Version Control**: Timestamped migration files
- **Environment-Specific**: Separate migrations for development and production

### 2. Model Design Principles

- **UUID Primary Keys**: All entities use UUID primary keys
- **Soft Deletes**: Implemented through timestamp fields
- **Audit Fields**: Created/updated timestamps on all entities
- **Relationship Modeling**: Proper foreign key relationships with cascades

### 3. Data Integrity

- **Constraints**: Database-level constraints for data integrity
- **Validations**: Model-level validations for business rules
- **Transactions**: Proper transaction boundaries for data consistency

## Testing Structure

### 1. Test Organization

```
tests/
├── integration/                 # Full-stack tests
│   ├── test_accounts.py         # User account integration tests
│   ├── test_todos.py            # Todo management integration tests
│   ├── test_health.py           # Health check integration tests
│   └── conftest.py              # Integration test configuration
├── unit/                        # Unit tests
│   ├── test_cli.py              # CLI command tests
│   ├── lib/                     # Library component tests
│   │   ├── test_settings.py     # Configuration tests
│   │   ├── test_crypt.py        # Cryptography tests
│   │   └── ...
│   └── conftest.py              # Unit test configuration
├── conftest.py                  # Global test configuration
├── data_fixtures.py             # Test data fixtures
└── helpers.py                   # Test helper utilities
```

### 2. Testing Strategy

- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: End-to-end tests with real database
- **Fixtures**: Reusable test data and setup
- **Coverage**: Comprehensive test coverage requirements

### 3. Test Database

- **Separate Database**: Isolated test database configuration
- **Transactions**: Test isolation through database transactions
- **Fixtures**: Automated test data setup and teardown

## Deployment Structure

### 1. Docker Configuration

```
deploy/
├── docker/
│   ├── dev/
│   │   └── Dockerfile           # Development Docker image
│   └── run/
│       ├── Dockerfile           # Production Docker image
│       └── Dockerfile.distroless # Distroless production image
└── docker-compose.infra.yml     # Infrastructure services
```

### 2. Environment Configuration

- **Development**: Hot reloading, debug logging, SQLite database
- **Production**: Optimized builds, PostgreSQL, structured logging
- **Testing**: In-memory database, minimal services

### 3. Infrastructure Services

- **PostgreSQL**: Primary database service
- **Redis**: Caching and session storage (if needed)
- **Nginx**: Reverse proxy and static file serving (production)

## Package Dependencies

### 1. Core Dependencies

- **`litestar[jwt,structlog]`**: Web framework with JWT and structured logging
- **`advanced-alchemy[uuid]`**: SQLAlchemy integration with UUID support
- **`asyncpg`**: PostgreSQL async driver
- **`pydantic[email]`**: Data validation with email support

### 2. Development Dependencies

- **`pytest`** + plugins: Testing framework
- **`ruff`**: Linting and formatting
- **`mypy`** + **`pyright`**: Type checking
- **`pre-commit`**: Git hooks for code quality

### 3. AI Integration

- **`openai-agents[litellm]`**: AI agent framework
- **`ace-framework`**: Agent collaboration framework

### 4. Production Dependencies

- **`litestar-granian`**: High-performance ASGI server
- **`boto3`**: AWS SDK for S3 integration
- **`passlib[argon2]`**: Password hashing

## Module Relationships

### 1. Dependency Flow

```
Controllers → Services → Repositories → Models
     ↓           ↓            ↓
   Schemas → DTOs → Domain Objects → Database
```

### 2. Import Patterns

- **Relative Imports**: Within the same domain
- **Absolute Imports**: Cross-domain imports
- **Type Checking**: TYPE_CHECKING imports for type hints
- **Circular Imports**: Avoided through proper dependency management

### 3. Plugin Architecture

The application uses Litestar's plugin system for:
- **Database Integration**: Advanced Alchemy plugin
- **Logging**: Structured logging plugin
- **Security**: JWT and OAuth plugins
- **Performance**: Granian server plugin

## Naming Conventions

### 1. File Naming

- **`snake_case`**: All Python files and directories
- **`kebab-case`**: Docker compose files and some configuration files
- **`UPPER_CASE`**: Environment variables and constants

### 2. Class Naming

- **`PascalCase`**: All class definitions
- **`Service`**: Business logic services (`TodoService`)
- **`Controller`**: HTTP controllers (`TodoController`)
- **`Repository`**: Data access (`TodoRepository`)

### 3. Function and Variable Naming

- **`snake_case`**: Functions and variables
- **`_private`**: Private methods and variables
- **`__dunder__`**: Special methods (constructors, operators)

### 4. Database Naming

- **`snake_case`**: Table names and column names
- **`plural`**: Table names (`todos`, `users`)
- **`foreign_key_id`**: Foreign key columns (`user_id`, `todo_id`)

## Best Practices and Guidelines

### 1. Code Organization

- **Single Responsibility**: Each module has a single, well-defined purpose
- **Dependency Injection**: Use DI for testability and loose coupling
- **Type Hints**: Comprehensive type annotations throughout
- **Documentation**: Docstrings for all public APIs

### 2. Development Workflow

- **Feature Branches**: All work done on feature branches
- **Code Review**: Peer review for all changes
- **Automated Testing**: Comprehensive test coverage
- **CI/CD**: Automated build, test, and deployment

### 3. Security Considerations

- **Input Validation**: All user input validated and sanitized
- **Authentication**: JWT-based authentication with proper token handling
- **Authorization**: Role-based access control
- **Secret Management**: Environment-based secret handling

This application structure provides a solid foundation for scalable, maintainable web application development following modern Python best practices and architectural patterns.