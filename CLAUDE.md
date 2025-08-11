# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development
- `make install` - Install dependencies and set up the development environment
- `make dev` - Run the application in development mode with auto-reload
- `make run` - Run the application in production mode
- `make test` - Run the test suite
- `make test-all` - Run all tests including those marked with custom markers
- `make coverage` - Run tests with coverage report
- `make lint` - Run all linting tools (ruff, pyright, slotscheck)
- `make fix` - Fix code formatting issues with ruff
- `make type-check` - Run type checking (pyright)

### Database
- `uv run app database make-migrations` - Create migration
- `uv run app database upgrade` - Run database migrations
- `uv run app database downgrade` - Rollback database migrations

### Docker
- `make start-infra` - Start local infrastructure (PostgreSQL)
- `make stop-infra` - Stop local infrastructure
- `make wipe-infra` - Remove local container data

### CLI
- `uv run app user create` - Create a new user
- `uv run app user promote` - Promote a user to admin
- `uv run app user demote` - Demote a user from admin

## Architecture

### Framework
- **Litestar** - ASGI web framework with built-in OpenAPI support
- **Advanced Alchemy** - SQLAlchemy integration with repository pattern
- **Pydantic** - Data validation and serialization
- **OpenAI Agents** - AI agent integration for natural language todo management

### Key Components

#### Application Structure
- `src/app/server/core.py` - Main application configuration plugin
- `src/app/config/` - Configuration management (app.py, base.py)
- `src/app/domain/` - Domain-driven design structure
- `src/app/db/` - Database models, migrations, and fixtures
- `src/app/lib/` - Shared utilities and dependencies

#### Domain Structure
- `accounts/` - User management, authentication, roles
- `todo/` - Todo item management with AI agent integration
- `system/` - System-level controllers and health checks

#### AI Agent Integration
The application includes an AI-powered todo assistant using OpenAI Agents:
- `src/app/domain/todo/todo_agents.py` - Agent implementation with function tools
- `src/app/domain/todo/controllers/todos.py` - REST API endpoints including agent endpoint
- Agent supports natural language todo creation, updates, deletion, and searching
- Uses Volcengine's Doubao model (configured in settings)

#### Database Models
- `User` - User accounts with OAuth support
- `Role` / `UserRole` - Role-based access control
- `Todo` - Todo items with importance levels and plan times
- `Tag` / `TodoTag` - Tagging system for todos
- `Importance` - Enum for todo importance levels

#### Authentication & Authorization
- JWT-based authentication using Litestar's built-in JWT support
- Role-based access control with guards
- OAuth integration with GitHub
- User context injection via dependencies

### Configuration
- Environment-based configuration using `.env` files
- Settings managed through `src/app/config/base.py`
- Database configuration supports PostgreSQL (primary) and SQLite (testing)
- AI configuration for Volcengine API integration

### Testing
- pytest for test execution
- Integration tests in `tests/integration/`
- Unit tests in `tests/unit/`
- Test fixtures and helpers in `tests/`
- Database testing with pytest-databases

### Code Style & Quality
- **Ruff** - Linting and formatting (configured in pyproject.toml)
- **Mypy** - Static type checking
- **Pyright** - Additional type checking
- **Pre-commit** - Git hooks for code quality
- **Slotscheck** - __slots__ usage verification

### Database Migrations
- Alembic for database migrations
- Migration files in `src/app/db/migrations/versions/`
- Automatic migration generation with `app database revision`

### Development Workflow
1. Use `make install` to set up the development environment
2. Run `make start-infra` to start PostgreSQL
3. Use `make dev` for development with auto-reload
4. Run `make lint` before committing
5. Use `make test` to run the test suite
6. Create migrations with `uv run app database revision` after model changes

### Key Dependencies
- `litestar[jwt,structlog]` - Web framework with JWT and structured logging
- `advanced-alchemy[uuid]` - SQLAlchemy integration
- `openai-agents` - AI agent framework
- `asyncpg` - PostgreSQL async driver
- `passlib[argon2]` - Password hashing
- `boto3` - AWS SDK (for S3 integration)
- `pytest` + related plugins - Testing framework

### Environment Variables
Required environment variables (see `.env.local.example`):
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Application secret key
- `VOLCENGINE_API_KEY` - AI service API key
- `VOLCENGINE_BASE_URL` - AI service base URL
- GitHub OAuth credentials for social login