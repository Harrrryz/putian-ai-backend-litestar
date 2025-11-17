# Development Infrastructure

This section provides comprehensive documentation for the development infrastructure that supports efficient, productive, and consistent development workflows.

## Table of Contents

- [Overview](#overview)
- [Docker Development Setup](#docker-development-setup)
- [Make Commands and Development Scripts](#make-commands-and-development-scripts)
- [Development Workflow Automation](#development-workflow-automation)
- [Local Infrastructure Setup](#local-infrastructure-setup)
- [Development Environment Orchestration](#development-environment-orchestration)
- [Build and Packaging Processes](#build-and-packaging-processes)
- [Development Tools Integration](#development-tools-integration)
- [Configuration Management](#configuration-management)
- [Best Practices and Workflows](#best-practices-and-workflows)

## Overview

The development infrastructure is built around modern Python development practices using:

- **UV Package Manager** - Fast Python package installation and management
- **Docker Compose** - Containerized development environments
- **Make** - Command automation and workflow orchestration
- **Multi-stage Docker builds** - Optimized production images
- **Comprehensive tooling** - Linting, formatting, testing, and type checking

The infrastructure supports both local development and containerized workflows, providing flexibility for different development preferences and team requirements.

## Docker Development Setup

### Docker Architecture

The project uses a multi-layered Docker approach with different configurations for development and production:

#### Development Dockerfile
```dockerfile
# Location: deploy/docker/dev/Dockerfile
FROM python:3.13-slim-bookworm AS python-base
# Development-specific optimizations
# - All development dependencies installed
# - Volume mounts for live reloading
# - Debug tools and utilities
```

#### Production Dockerfile
```dockerfile
# Location: deploy/docker/run/Dockerfile
# Multi-stage build for optimized production images
# - Minimal runtime base
# - Compiled dependencies only
# - Security-hardened non-root user
```

### Docker Compose Configurations

#### Infrastructure Services
```yaml
# deploy/docker-compose.infra.yml
services:
  db:
    image: postgres:latest
    ports:
      - "15432:5432"
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app"]
```

#### Development Override
```yaml
# docker-compose.override.yml
services:
  app:
    build:
      context: .
      dockerfile: deploy/docker/dev/Dockerfile
    volumes:
      - ./src:/workspace/app/src
      - ./tests:/workspace/app/tests
    command: litestar run --reload --host 0.0.0.0 --port 8000
```

#### Full Stack Deployment
```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: deploy/docker/run/Dockerfile
    depends_on:
      db:
        condition: service_healthy

  migrator:
    build:
      context: .
      dockerfile: deploy/docker/run/Dockerfile
    command: litestar database upgrade --no-prompt
    depends_on:
      db:
        condition: service_healthy
```

### Docker Development Workflows

#### Starting Development Environment
```bash
# Start infrastructure only
make start-infra

# Start full development stack
docker-compose up --build

# Start with live reload
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

#### Production Deployment
```bash
# Build and deploy production stack
docker-compose -f docker-compose.yml up --build -d

# Run migrations
docker-compose run --rm migrator
```

### Docker Optimization Features

#### Multi-stage Builds
- **Builder Stage**: Compiles all dependencies and builds wheels
- **Runner Stage**: Minimal runtime with only production dependencies
- **Security**: Non-root user, minimal attack surface

#### Layer Caching
- Dependencies installed separately from application code
- Optimized for Docker layer caching
- Faster rebuilds during development

#### Health Checks
- Database readiness validation
- Application health endpoints
- Automated service startup ordering

## Make Commands and Development Scripts

The Makefile provides a comprehensive command interface for all development activities:

### Installation and Setup Commands

```makefile
# Fresh installation with all dependencies
install: destroy clean
    uv sync --all-extras --dev
    npm install --no-fund

# Install UV package manager
install-uv:
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Upgrade all dependencies
upgrade:
    uv lock --upgrade
    npm upgrade --latest
    pre-commit autoupdate
```

### Application Runtime Commands

```makefile
# Development mode with auto-reload
dev:
    APP_ENV=development uv run app run --reload

# Production mode
run:
    APP_ENV=production uv run app run
```

### Testing Commands

```makefile
# Run basic test suite
test:
    uv run pytest tests -n 2 --quiet

# Run all tests including custom markers
test-all:
    uv run pytest tests -m '' -n 2 --quiet

# Generate coverage report
coverage:
    uv run pytest tests --cov -n auto --quiet
    uv run coverage html
    uv run coverage xml
```

### Code Quality Commands

```makefile
# Run all formatters
fix:
    uv run ruff check --fix --unsafe-fixes

# Run all linting checks
lint: pre-commit type-check slotscheck

# Type checking with multiple tools
type-check: mypy pyright

# Pre-commit hooks
pre-commit:
    uv run pre-commit run --color=always --all-files
```

### Database Commands

```makefile
# Create new migration
make-migrations:
    uv run app database make-migrations

# Apply migrations
database-upgrade:
    uv run app database upgrade

# Rollback migrations
database-downgrade:
    uv run app database downgrade
```

### Documentation Commands

```makefile
# Build documentation
docs: docs-clean
    uv run sphinx-build -M html docs docs/_build/ -E -a -j auto

# Serve docs locally
docs-serve:
    uv run sphinx-autobuild docs docs/_build/ -j auto

# Check documentation links
docs-linkcheck:
    uv run sphinx-build -b linkcheck ./docs ./docs/_build
```

### Infrastructure Commands

```makefile
# Start local development infrastructure
start-infra:
    docker compose -f deploy/docker-compose.infra.yml up -d

# Stop infrastructure
stop-infra:
    docker compose -f deploy/docker-compose.infra.yml down

# Clean up infrastructure data
wipe-infra:
    docker compose -f deploy/docker-compose.infra.yml down -v --remove-orphans

# View infrastructure logs
infra-logs:
    docker compose -f deploy/docker-compose.infra.yml logs -f
```

### Build and Release Commands

```makefile
# Clean build artifacts
clean:
    rm -rf pytest_cache .ruff_cache build/ dist/ .coverage
    find . -name '*.pyc' -delete
    find . -name '__pycache__' -exec rm -rf {} +

# Build distribution packages
build:
    uv build

# Create release with version bump
release:
    make clean
    uv run bump-my-version bump $(bump)
    make build
```

## Development Workflow Automation

### Cross-Platform Compatibility

The Makefile includes OS detection for Windows, macOS, and Linux:

```makefile
# OS Detection
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        DETECTED_OS := macOS
    else ifeq ($(UNAME_S),Linux)
        DETECTED_OS := Linux
    endif
endif

# Platform-specific commands
dev:
ifeq ($(DETECTED_OS),Windows)
    powershell -noprofile -Command "$$env:APP_ENV='development'; uv run app run --reload"
else
    APP_ENV=development uv run app run --reload
endif
```

### Automated Quality Gates

#### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

#### Comprehensive Linting Pipeline
```bash
# Full quality check pipeline
make check-all  # Runs: lint test-all coverage
```

### Dependency Management

#### UV Package Manager Integration
```toml
# pyproject.toml
[dependency-groups]
dev = [
    { include-group = "docs" },
    { include-group = "linting" },
    { include-group = "test" },
]

[tool.uv]
default-groups = ["dev", "docs", "linting", "test"]
```

#### Lock File Management
```makefile
# Rebuild lockfiles from scratch
lock:
    uv lock --upgrade

# Upgrade all dependencies
upgrade:
    uv lock --upgrade
    uv run npm upgrade --latest
```

## Local Infrastructure Setup

### Database Infrastructure

#### PostgreSQL Configuration
```yaml
# deploy/docker-compose.infra.yml
services:
  db:
    image: postgres:latest
    ports:
      - "15432:5432"  # Custom port to avoid conflicts
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app"]
      interval: 2s
      timeout: 3s
      retries: 40
```

#### Connection Configuration
```python
# Environment-based database configuration
DATABASE_URL = "postgresql+asyncpg://app:app@127.0.0.1:15432/app"

# Production Docker environment
DATABASE_URL = "postgresql+asyncpg://app:app@db:5432/app"
```

### Development Tools Integration

#### Python Environment
- **UV Package Manager**: Fast dependency installation and management
- **Virtual Environment**: Isolated Python environment with `.venv`
- **Node.js Integration**: Automatically installed for frontend tooling

#### Database Tools
```bash
# Create migrations
uv run app database make-migrations

# Apply migrations
uv run app database upgrade

# Database CLI access
uv run app database --help
```

### Environment Configuration

#### Development Environment
```bash
# .env.local.example
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app
LITESTAR_DEBUG=true
LOG_LEVEL=10
DATABASE_ECHO=true
```

#### Docker Environment
```bash
# .env.docker.example
DATABASE_URL=postgresql+asyncpg://app:app@db:5432/app
LITESTAR_DEBUG=true
LOG_LEVEL=20
ALLOWED_CORS_ORIGINS=["localhost:3006","localhost:8080","localhost:8000"]
```

## Development Environment Orchestration

### Multi-Environment Support

#### Local Development
```bash
# Setup local development
make install          # Install dependencies
make start-infra      # Start PostgreSQL
make dev             # Start application with reload
```

#### Docker Development
```bash
# Full Docker development workflow
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build
```

#### Production Simulation
```bash
# Production-like environment locally
docker-compose -f docker-compose.yml up --build -d
```

### Service Dependencies

#### Database Health Checks
```yaml
depends_on:
  db:
    condition: service_healthy

healthcheck:
  test: ["CMD", "pg_isready", "-U", "app"]
  interval: 2s
  timeout: 3s
  retries: 40
```

#### Migration Workflow
```yaml
migrator:
  build:
    context: .
    dockerfile: deploy/docker/run/Dockerfile
  command: litestar database upgrade --no-prompt
  depends_on:
    db:
      condition: service_healthy
```

### Development Features

#### Live Reloading
```bash
# Automatic code reloading in development
make dev  # or
docker-compose run --rm app litestar run --reload
```

#### Volume Mounts
```yaml
volumes:
  - ./src:/workspace/app/src        # Source code
  - ./tests:/workspace/app/tests    # Test files
  - ./docs:/workspace/app/docs      # Documentation
```

#### Debug Configuration
```python
# Development debugging settings
LITESTAR_DEBUG=true
LOG_LEVEL=10
DATABASE_ECHO=true
```

## Build and Packaging Processes

### UV Build System

#### Project Configuration
```toml
# pyproject.toml
[build-system]
build-backend = "hatchling.build"
requires = ["hatchling", "setuptools"]

[tool.hatch.build]
dev-mode-dirs = ["src", "."]
sources = ["src"]
```

#### Build Commands
```makefile
build:
    uv build

release:
    make clean
    uv run bump-my-version bump $(bump)
    make build
```

### Docker Build Optimization

#### Multi-stage Builds
```dockerfile
# Builder stage - compiles all dependencies
FROM python:3.13-slim-bookworm AS builder
RUN uv venv && uv sync --no-dev
RUN uv build

# Runner stage - minimal runtime
FROM python:3.13-slim-bookworm AS runner
COPY --from=builder /workspace/app/dist /tmp/
RUN uv pip install /tmp/*.whl
```

#### Build Arguments
```dockerfile
ARG PYTHON_BUILDER_IMAGE=3.13-slim-bookworm
ARG UV_INSTALL_ARGS="--no-dev"
ARG ENV_SECRETS="runtime-secrets"
ARG LITESTAR_APP="app.asgi:create_app"
```

### Distribution Packages

#### Wheel Building
```bash
# Build source and wheel distributions
uv build

# Output files
dist/
├── app-0.2.0-py3-none-any.whl
└── app-0.2.0.tar.gz
```

#### Installation from Wheels
```bash
# Install from built wheel
uv pip install dist/app-0.2.0-py3-none-any.whl
```

## Development Tools Integration

### Code Quality Tools

#### Ruff (Linting and Formatting)
```toml
# pyproject.toml
[tool.ruff]
line-length = 120
lint.select = ["ALL"]
lint.fixable = ["ALL"]
lint.ignore = [
    "E501",    # Line too long (handled by formatter)
    "D100",    # Missing docstring in public module
    # ... other ignores
]

[tool.ruff.lint.isort]
known-first-party = ['tests', 'app']
```

#### Type Checking
```toml
# MyPy configuration
[tool.mypy]
strict = true
warn_return_any = true
warn_unreachable = true
plugins = []

# Pyright configuration
[tool.pyright]
include = ["src/app", "tests"]
exclude = ["scripts", "docs"]
```

#### Slot Checking
```toml
[tool.slotscheck]
strict-imports = false
```

### Testing Tools

#### Pytest Configuration
```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = ["-ra", "--ignore", "migrations"]
testpaths = ["tests"]
filterwarnings = [
    "ignore::DeprecationWarning:pkg_resources",
    "ignore::DeprecationWarning:google.*",
]
```

#### Coverage Configuration
```toml
[tool.coverage.run]
branch = true
omit = ["tests/*", "**/*/migrations/**/*.py", "tools/*"]

[tool.coverage.report]
exclude_lines = [
    'if TYPE_CHECKING:',
    'pragma: no cover',
    'if __name__ == .__main__.:',
    'def __repr__',
]
show_missing = true
```

### Documentation Tools

#### Sphinx Configuration
```bash
# Build documentation
make docs

# Serve with live reload
make docs-serve

# Check links
make docs-linkcheck
```

#### Documentation Dependencies
```toml
# pyproject.toml
docs = [
  "sphinx",
  "sphinx-autobuild",
  "sphinx-copybutton",
  "sphinx-toolbox",
  "sphinx-design",
  "sphinx-click",
  "sphinxcontrib-mermaid",
  "shibuya",
]
```

## Configuration Management

### Environment-Based Configuration

#### Multiple Environment Files
```bash
.env.local.example     # Local development template
.env.development       # Development settings
.env.testing          # Test environment
.env.production       # Production settings
.env.docker.example   # Docker environment
```

#### Configuration Structure
```python
# src/app/config/base.py
from pydantic import BaseSettings

class DatabaseSettings(BaseSettings):
    url: str
    echo: bool = False
    pool_size: int = 5

    class Config:
        env_prefix = "DATABASE_"

class AppSettings(BaseSettings):
    secret_key: str
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "LITESTAR_"
```

### Environment Variables

#### Core Application Settings
```bash
# Application
SECRET_KEY='your-secret-key'
LITESTAR_DEBUG=true
LITESTAR_HOST=0.0.0.0
LITESTAR_PORT=8000
APP_URL=http://localhost:8000

# Logging
LOG_LEVEL=10

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DATABASE_ECHO=true
DATABASE_POOL_SIZE=5
```

#### External Service Configuration
```bash
# S3 Storage
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket
S3_ENDPOINT_URL=https://endpoint-url
S3_REGION=your-region

# SMTP/Email
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Runtime Configuration

#### Application Factory
```python
# src/app/asgi.py
from litestar import Litestar

def create_app() -> Litestar:
    return Litestar(
        route_handlers=[],
        on_app_init=[AppConfigHook()],
    )
```

#### Configuration Loading
```python
# src/app/server/core.py
def get_app_config() -> AppConfig:
    return AppConfig(
        app_name=settings.app.NAME,
        debug=settings.app.DEBUG,
        prefer_coroutine_http_handlers=True,
    )
```

## Best Practices and Workflows

### Development Workflow

#### 1. Initial Setup
```bash
# Clone and setup
git clone <repository>
cd <project>
make install              # Install all dependencies
make start-infra          # Start local infrastructure
```

#### 2. Daily Development
```bash
# Start development environment
make start-infra          # Start database
make dev                  # Start application with reload

# Make changes and test
make test                 # Run tests
make lint                 # Check code quality
make fix                  # Fix formatting issues
```

#### 3. Before Commit
```bash
# Full quality check
make check-all            # Run all checks
make docs                 # Update documentation
```

#### 4. Release Process
```bash
# Prepare release
make clean                # Clean artifacts
make release bump=patch   # Bump version and build
```

### Development Tips

#### Efficient Testing
```bash
# Run specific tests
uv run pytest tests/unit/test_specific.py -v

# Run with coverage for specific files
uv run pytest tests --cov=src.app.domain.todo --cov-report=term-missing

# Parallel test execution
uv run pytest tests -n auto
```

#### Database Management
```bash
# Create migration after model changes
uv run app database make-migrations

# Apply migrations safely
uv run app database upgrade --no-prompt

# Check database status
uv run app database info
```

#### Debugging Setup
```python
# Development debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Database query logging
settings.db.ECHO = True
```

### Performance Optimization

#### Development Performance
```bash
# Use UV for faster dependency management
uv sync --no-install-project  # Install dependencies first
uv sync                        # Then install project

# Parallel test execution
pytest -n auto                 # Use all CPU cores
```

#### Docker Performance
```yaml
# Optimize Docker builds
.dockerignore:
  .git
  .venv
  *.pyc
  __pycache__
  .coverage
  htmlcov/
```

#### Memory Management
```python
# Connection pooling
database_pool_size = 5
database_max_overflow = 10
database_pool_timeout = 30

# Async configuration
asyncio_event_loop_policy = "uvloop"
```

### Troubleshooting

#### Common Issues

**Port Conflicts**
```bash
# Check port usage
netstat -an | grep :5432
lsof -i :5432

# Use different port in .env
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15433/app
```

**Dependency Issues**
```bash
# Clean and reinstall
make destroy
make clean
make install

# Rebuild lockfile
make lock
```

**Database Connection Issues**
```bash
# Check database status
docker compose -f deploy/docker-compose.infra.yml ps
docker compose -f deploy/docker-compose.infra.yml logs db

# Reset database
make wipe-infra
make start-infra
```

#### Debug Mode
```bash
# Enable full debugging
LITESTAR_DEBUG=true
LOG_LEVEL=10
DATABASE_ECHO=true

# Run with debugger
uv run python -m debugpy --listen 5678 --wait-for-client -m app
```

This comprehensive development infrastructure provides a robust, efficient, and productive environment for developing the Litestar application, supporting both individual developers and team collaboration workflows.