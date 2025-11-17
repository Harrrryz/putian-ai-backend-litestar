# Development Setup & Environment

This comprehensive guide covers everything you need to set up a productive development environment for the Litestar Todo Backend with OpenAI Agents SDK integration.

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites Installation](#prerequisites-installation)
- [Development Environment Setup](#development-environment-setup)
- [IDE Configuration](#ide-configuration)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Development Workflow](#development-workflow)
- [Testing Setup](#testing-setup)
- [Code Quality Tools](#code-quality-tools)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Development Commands](#development-commands)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Python**: 3.11+ (3.13 recommended)
- **Node.js**: 18.0+ (22.16.0+ recommended)
- **npm**: 8.0+ (10.9.2+ recommended)
- **Docker**: 20.0+ (26.1.1+ recommended)
- **Git**: 2.30+
- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)

### Recommended Hardware
- **RAM**: 8GB+ (16GB recommended for AI development)
- **Storage**: 10GB+ free space
- **CPU**: Multi-core processor recommended

## Prerequisites Installation

### 1. Install UV Package Manager

UV is a fast Python package manager that we use for dependency management:

```bash
# Install UV (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use the Make command
make install-uv

# For Windows, use PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install Node.js and npm

Option 1: Download from [nodejs.org](https://nodejs.org/)
Option 2: Use version manager (recommended):

```bash
# Install nvm (Linux/macOS)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install and use Node.js 22
nvm install 22
nvm use 22
```

### 3. Install Docker

Download and install Docker Desktop from [docker.com](https://docker.com/):

- **Windows**: Docker Desktop for Windows with WSL2
- **macOS**: Docker Desktop for Mac
- **Linux**: Install Docker Engine and Docker Compose

### 4. Git Configuration

Ensure your Git is properly configured:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd putian-ai-todo-back-end-litestar
```

### 2. Install Dependencies

The project uses a sophisticated setup with both Python and Node.js dependencies:

```bash
# Complete setup with virtual environment and all dependencies
make install

# Or manually:
# Create virtual environment and install Python dependencies
uv python pin 3.13
uv venv
uv sync --all-extras --dev

# Install Node.js environment and dependencies
uvx nodeenv .venv --force --quiet
NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm install --no-fund
```

### 3. Start Local Infrastructure

The application requires PostgreSQL for development:

```bash
# Start PostgreSQL container
make start-infra

# Or manually:
docker compose -f deploy/docker-compose.infra.yml up -d
```

### 4. Set Up Environment Configuration

Copy the environment configuration file:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` with your configuration:

```bash
# Required minimum configuration
SECRET_KEY='your-secret-key-here'
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app

# Optional but recommended
LITESTAR_DEBUG=true
LITESTAR_HOST=0.0.0.0
LITESTAR_PORT=8089

# For AI features (required for todo agents)
VOLCENGINE_API_KEY='your-api-key'
VOLCENGINE_BASE_URL='your-base-url'
```

### 5. Database Setup

Initialize the database with migrations:

```bash
# Run database migrations
uv run app database upgrade

# Or use the Litestar CLI
uv run litestar db upgrade
```

### 6. Verify Installation

Test that everything is working:

```bash
# Run the application in development mode
make dev

# Or manually:
APP_ENV=development uv run app run --reload
```

Visit http://localhost:8089 to see the running application.

## IDE Configuration

### VS Code Setup

1. **Install Recommended Extensions**:
   - Python (Microsoft)
   - Pylance (Microsoft)
   - Python Docstring Generator
   - GitLens
   - Docker
   - SQLite Viewer
   - Thunder Client (for API testing)

2. **Workspace Settings** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "./.venv/Scripts/python.exe",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".mypy_cache": true,
    ".ruff_cache": true
  }
}
```

3. **Debug Configuration** (`.vscode/launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Litestar App",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/app/__main__.py",
      "args": ["run", "--debug"],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "APP_ENV": "development"
      }
    }
  ]
}
```

### PyCharm Setup

1. **Project Structure**: Mark `src` as Sources Root
2. **Python Interpreter**: Point to `.venv/Scripts/python.exe`
3. **Code Style**: Configure to use Black formatter
4. **Inspections**: Enable mypy and pylint
5. **Run/Debug Configurations**: Create configuration for `app run --reload`

### Vim/Neovim Setup

If you prefer Vim editors, here's a minimal setup:

```lua
-- For Neovim with lazy.nvim
return {
  'neovim/nvim-lspconfig',
  config = function()
    require('lspconfig').pyright.setup{}
    require('lspconfig').ruff_lsp.setup{}
  end
}
```

## Database Setup

### Development Database

The development setup uses Docker Compose to run PostgreSQL:

```yaml
# deploy/docker-compose.infra.yml
services:
  db:
    image: postgres:latest
    ports:
      - "15432:5432"
    environment:
      POSTGRES_PASSWORD: "app"
      POSTGRES_USER: "app"
      POSTGRES_DB: "app"
```

### Database Migration Commands

```bash
# Create new migration
uv run app database make-migrations --message "your migration message"

# Apply migrations
uv run app database upgrade

# Rollback migrations
uv run app database downgrade

# Show current revision
uv run app database current
```

### Database Connection

The application connects to PostgreSQL using:

- **Host**: 127.0.0.1:15432
- **Database**: app
- **Username**: app
- **Password**: app

### Testing Database

For testing, the application automatically uses SQLite in-memory database, but you can configure PostgreSQL for tests too:

```bash
# Test with PostgreSQL
uv run pytest tests --db-url postgresql+asyncpg://app:app@127.0.0.1:15432/app_test
```

## Configuration

### Environment Variables

Key environment variables for development:

```bash
# App Configuration
SECRET_KEY='your-secret-key-here'
APP_ENV=development
LITESTAR_DEBUG=true
LITESTAR_HOST=0.0.0.0
LITESTAR_PORT=8089
APP_URL=http://localhost:8089

# Database
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app
DATABASE_ECHO=true
DATABASE_ECHO_POOL=true

# Logging
LOG_LEVEL=10

# AI Configuration (required for todo agents)
VOLCENGINE_API_KEY='your-volcengine-api-key'
VOLCENGINE_BASE_URL='your-volcengine-base-url'

# Optional: S3 Configuration
S3_ACCESS_KEY='your-access-key'
S3_SECRET_KEY='your-secret-key'
S3_BUCKET_NAME='your-bucket'
S3_ENDPOINT_URL='your-endpoint'
S3_REGION='your-region'

# Optional: SMTP Configuration
SMTP_USERNAME='your-smtp-username'
SMTP_PASSWORD='your-smtp-password'
SMTP_HOST='smtp.maileroo.com'
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Configuration Files

- `src/app/config/base.py` - Main configuration classes
- `src/app/config/app.py` - Application-specific settings
- `.env.local` - Local development environment variables

## Development Workflow

### 1. Development Mode

Run the application with auto-reload:

```bash
make dev

# Application will be available at http://localhost:8089
# OpenAPI docs at http://localhost:8089/schema/swagger
```

### 2. Making Changes

The development server automatically restarts when you change Python files. For static assets or configuration changes, you may need to restart manually.

### 3. Database Changes Workflow

When making model changes:

1. **Modify models** in `src/app/db/models/`
2. **Create migration**: `uv run app database make-migrations`
3. **Review migration** in `src/app/db/migrations/versions/`
4. **Apply migration**: `uv run app database upgrade`

### 4. Testing Workflow

Before committing changes:

```bash
# Run all quality checks
make check-all

# Or run step by step:
make lint      # Code quality and formatting
make test      # Run tests
make coverage  # Test coverage report
```

### 5. Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add your feature description"

# Run checks before pushing
make check-all

# Push and create PR
git push origin feature/your-feature-name
```

## Testing Setup

### Test Framework

The project uses **pytest** with these key plugins:
- `pytest-xdist` - Parallel test execution
- `pytest-mock` - Mocking utilities
- `pytest-cov` - Coverage reporting
- `pytest-databases` - Database testing utilities
- `pytest-sugar` - Enhanced output formatting

### Running Tests

```bash
# Run all tests
make test

# Run all tests including those with custom markers
make test-all

# Run tests with coverage
make coverage

# Run tests in parallel
uv run pytest tests -n auto

# Run specific test file
uv run pytest tests/unit/test_todo.py -v

# Run tests with specific marker
uv run pytest tests -m "integration"
```

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── conftest.py     # Test fixtures and configuration
└── helpers/        # Test utilities
```

### Test Database

Tests automatically use a separate database. You can configure it with environment variables:

```bash
# For PostgreSQL tests
TEST_DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app_test

# Run tests with specific database
uv run pytest tests --db-url $TEST_DATABASE_URL
```

### Writing Tests

Example test structure:

```python
# tests/unit/test_todo.py
import pytest
from app.domain.todo.services import TodoService

class TestTodoService:
    async def test_create_todo(self, db_session, user_factory):
        # Arrange
        service = TodoService(session=db_session)
        user = await user_factory()

        # Act
        todo = await service.create_todo(
            title="Test Todo",
            user_id=user.id,
        )

        # Assert
        assert todo.title == "Test Todo"
        assert todo.user_id == user.id
```

## Code Quality Tools

### Ruff (Linter & Formatter)

Ruff is used for both linting and formatting:

```bash
# Check code quality
uv run ruff check src tests

# Format code
uv run ruff format src tests

# Fix auto-fixable issues
uv run ruff check --fix --unsafe-fixes src tests
```

#### Ruff Configuration

Configuration is in `pyproject.toml`:
- **Line length**: 120 characters
- **Target Python**: 3.11+
- **Code style**: Google docstring convention
- **Import sorting**: isort-compatible

### MyPy (Type Checker)

Static type checking with strict settings:

```bash
# Run mypy
make mypy

# Or manually:
uv run dmypy run src/app

# Check specific file
uv run mypy src/app/domain/todo/services.py
```

#### MyPy Configuration

- **Strict mode**: Enabled
- **Plugins**: SQLAlchemy support
- **Exclusions**: Build artifacts and migrations

### Pyright (Type Checker)

Alternative type checker from Microsoft:

```bash
# Run pyright
make pyright

# Or manually:
uv run pyright
```

#### Pyright Configuration

- **Include**: `src/app`, `tests`
- **Exclude**: `scripts`, `docs`
- **Type checking mode**: Strict

### Slotscheck

Ensures proper usage of `__slots__` for performance:

```bash
# Run slots check
make slotscheck
```

## Pre-commit Hooks

### Setup

Pre-commit hooks are automatically installed with `make install`. To set up manually:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks on all files
uv run pre-commit run --all-files
```

### Available Hooks

1. **Ruff**: Code formatting and linting
2. **Mypy**: Type checking
3. **Slotscheck**: Verify `__slots__` usage
4. **Codespell**: Spell checking
5. **Trailing whitespace**: Remove trailing spaces
6. **End of file**: Ensure proper file endings

### Pre-commit Configuration

Hooks are configured in the project's `pyproject.toml`. The configuration includes:

- Automatic code fixing where possible
- Fast execution with caching
- Parallel execution for multiple files

## Development Commands

### Make Commands Overview

The Makefile provides convenient commands for development:

```bash
# Setup and Installation
make install          # Complete fresh installation
make upgrade          # Upgrade all dependencies
make clean            # Clean temporary files
make destroy          # Remove virtual environment

# Development
make dev              # Run in development mode
make run              # Run in production mode

# Code Quality
make lint             # Run all linting tools
make type-check       # Run type checkers (mypy + pyright)
make fix              # Auto-fix code formatting issues
make slotscheck       # Check __slots__ usage

# Testing
make test             # Run test suite
make test-all         # Run all tests including marked ones
make coverage         # Run tests with coverage report
make check-all        # Run all checks (lint + test + coverage)

# Database
make start-infra      # Start local PostgreSQL
make stop-infra       # Stop local infrastructure
make wipe-infra       # Remove container data

# Documentation
make docs             # Build documentation
make docs-serve       # Serve docs locally
```

### CLI Commands

The application provides CLI commands via the Litestar CLI:

```bash
# Application commands
uv run app run                    # Start application
uv run app info                   # Show application info

# Database commands
uv run app database upgrade       # Apply migrations
uv run app database downgrade     # Rollback migrations
uv run app database current       # Show current migration

# User management
uv run app user create            # Create new user
uv run app user promote           # Promote user to admin
uv run app user demote            # Demote user from admin
```

## Troubleshooting

### Common Issues

#### 1. UV Installation Issues

**Problem**: UV not found after installation
**Solution**: Restart your terminal or add UV to PATH

```bash
# For Linux/macOS
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc

# For Windows (PowerShell)
[Environment]::SetEnvironmentVariable("PATH", "$env:PATH;$env:USERPROFILE\.cargo\bin", "User")
```

#### 2. Virtual Environment Issues

**Problem**: Python not found or import errors
**Solution**: Recreate virtual environment

```bash
make destroy
make install
```

#### 3. Database Connection Issues

**Problem**: Cannot connect to PostgreSQL
**Solution**: Check Docker container status

```bash
docker ps  # Check if container is running
make start-infra  # Restart if needed
```

#### 4. Permission Issues (Linux/macOS)

**Problem**: Permission denied errors
**Solution**: Fix file permissions

```bash
# Fix permissions for shell scripts
chmod +x tools/*.sh

# Fix virtual environment permissions
sudo chown -R $USER:$USER .venv
```

#### 5. Node.js Dependencies Issues

**Problem**: npm install fails
**Solution**: Clean and reinstall

```bash
# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm install --no-fund
```

#### 6. Port Already in Use

**Problem**: Port 8089 already in use
**Solution**: Kill process or change port

```bash
# Find process using port (Linux/macOS)
lsof -i :8089

# Kill process
kill -9 <PID>

# Or change port in .env.local
LITESTAR_PORT=8090
```

#### 7. Pre-commit Hook Issues

**Problem**: Pre-commit hooks fail
**Solution**: Run hooks manually to see detailed errors

```bash
# Run pre-commit manually
uv run pre-commit run --all-files --verbose

# Update pre-commit hooks
uv run pre-commit autoupdate
```

### Performance Tips

1. **Parallel Testing**: Use `pytest -n auto` for faster test runs
2. **Database Pooling**: Configure appropriate pool sizes for development
3. **UV Cache**: Keep UV cache for faster dependency resolution
4. **Docker Resources**: Allocate sufficient memory to Docker Desktop

### Getting Help

If you encounter issues not covered here:

1. Check the [application logs](#logging-and-debugging)
2. Review the [GitHub issues](https://github.com/your-repo/issues)
3. Consult the [Litestar documentation](https://docs.litestar.dev/)
4. Check the [OpenAI Agents SDK documentation](https://github.com/openai/openai-agents)

### Logging and Debugging

Enable debug logging for troubleshooting:

```bash
# Set log level to DEBUG
LOG_LEVEL=10 uv run app run --debug

# Or in .env.local
LOG_LEVEL=10
LITESTAR_DEBUG=true
```

Database query debugging:

```bash
# Enable SQL query logging
DATABASE_ECHO=true
DATABASE_ECHO_POOL=true
```

---

This setup guide should get you up and running with a productive development environment. If you encounter any issues or have suggestions for improving this guide, please submit an issue or pull request.