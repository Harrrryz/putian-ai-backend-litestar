# Getting Started Guide

Welcome to the AI-Powered Todo Backend! This comprehensive guide will help you set up the development environment and get familiar with the project's features and architecture.

## Project Overview

This is a sophisticated todo management backend built with **Litestar** and **OpenAI Agents SDK integration** that provides intelligent task management through conversational AI interfaces. The application combines traditional REST API endpoints with advanced AI-powered agent capabilities for a seamless user experience.

### Key Features

- **🤖 AI-Powered Todo Management**: Integrated OpenAI Agents for natural language todo creation, updates, and scheduling
- **🔒 User Isolation & Security**: JWT-based authentication with role-based access control
- **📝 Persistent Conversations**: AI agents remember previous interactions and maintain context
- **⚡ High Performance**: Async architecture with PostgreSQL and connection pooling
- **🏷️ Advanced Todo Features**: Tagging, importance levels, intelligent scheduling, and conflict detection
- **🔄 Real-time Updates**: Server-Sent Events for streaming AI responses
- **📊 Usage Tracking**: Built-in quota management and usage monitoring
- **🧪 Comprehensive Testing**: Full test coverage with integration and unit tests

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - Required runtime environment
- **Docker & Docker Compose** - For local infrastructure (PostgreSQL)
- **Git** - Version control
- **uv** - Fast Python package installer (optional, will be installed automatically)
- **Node.js & npm** - For frontend dependencies and development tools

### Optional: External Services

For full functionality, you may want to configure:
- **AI Provider**: VolcEngine API (for Doubao models) or other OpenAI-compatible APIs
- **Email Service**: SMTP configuration for user verification and password resets
- **Object Storage**: S3-compatible storage for file uploads

## Quick Start

Follow these steps to get the application running locally:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd putian-ai-todo-back-end-litestar
```

### 2. Install Dependencies

Use the Makefile for a complete setup:

```bash
make install
```

This command will:
- Create a Python virtual environment
- Install all Python dependencies from `pyproject.toml`
- Set up Node.js environment if needed
- Install frontend dependencies
- Configure development tools

### 3. Set Up Local Infrastructure

Start the PostgreSQL database:

```bash
make start-infra
```

This starts a PostgreSQL container on port `15432` with the following credentials:
- Host: `localhost`
- Port: `15432`
- Database: `app`
- Username: `app`
- Password: `app`

### 4. Configure Environment

Create your environment file by copying the example:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` and configure at least these required variables:

```bash
# Application
SECRET_KEY='your-secret-key-here'
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app

# AI Integration (optional but recommended)
VOLCENGINE_API_KEY='your-volcengine-api-key'
VOLCENGINE_BASE_URL='https://ark.cn-beijing.volces.com/api/v3'

# Email Configuration (optional)
SMTP_USERNAME='your-smtp-username'
SMTP_PASSWORD='your-smtp-password'
SMTP_HOST='smtp.your-provider.com'
SMTP_PORT=587
```

### 5. Run Database Migrations

Apply the database schema:

```bash
uv run app database upgrade
```

### 6. Create an Admin User

Create your first user with admin privileges:

```bash
uv run app user create --email admin@example.com --name "Admin User" --password your-secure-password --superuser
```

### 7. Start the Application

Run in development mode with auto-reload:

```bash
make dev
```

Or run in production mode:

```bash
make run
```

The application will be available at:
- **API Server**: http://localhost:8089
- **API Documentation**: http://localhost:8089/schema (Scalar UI)
- **Health Check**: http://localhost:8089/health

### 8. Verify the Setup

Test the health endpoint:

```bash
curl http://localhost:8089/health
```

You should see a JSON response indicating the application is healthy.

## Basic Usage Examples

### 1. Traditional REST API Usage

First, authenticate to get a JWT token:

```bash
curl -X POST "http://localhost:8089/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-secure-password"
  }'
```

Create a todo using the REST API:

```bash
curl -X POST "http://localhost:8089/api/todos" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Buy groceries",
    "description": "Get milk, bread, and eggs",
    "importance": "medium",
    "tags": ["shopping", "weekly"]
  }'
```

### 2. AI-Powered Todo Management

Use the AI agent for natural language todo creation:

```bash
curl -X POST "http://localhost:8089/api/todo-agents/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a todo for buying groceries tomorrow at 2 PM, mark it as high priority"
  }'
```

The AI agent will:
- Create the todo automatically
- Schedule it for tomorrow at 2 PM
- Set appropriate priority
- Provide a conversational response

Follow up with natural language:

```bash
curl -X POST "http://localhost:8089/api/todo-agents/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What todos do I have scheduled for tomorrow?"
  }'
```

### 3. Streaming Chat Interface

For real-time responses, use the streaming endpoint:

```bash
curl -X GET "http://localhost:8089/api/todo-agents/chat/stream?message=Schedule%20a%20meeting%20for%20Monday" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Accept: text/event-stream"
```

### 4. Session Management

View conversation history with the AI agent:

```bash
curl -X GET "http://localhost:8089/api/agent-sessions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Development Workflow

### Common Development Commands

```bash
# Install dependencies
make install

# Start development server with auto-reload
make dev

# Run tests
make test

# Run tests with coverage
make coverage

# Run all linting checks
make lint

# Fix code formatting issues
make fix

# Run type checking
make type-check
```

### Database Management

```bash
# Create new migration
uv run app database revision --message "Add new feature"

# Apply migrations
uv run app database upgrade

# Rollback migration
uv run app database downgrade

# View current migration status
uv run app database current
```

### User Management CLI

```bash
# Create regular user
uv run app user create --email user@example.com --name "Regular User" --password password123

# Promote user to admin
uv run app user promote --email user@example.com

# Demote user from admin
uv run app user demote --email user@example.com
```

### Infrastructure Management

```bash
# Start local PostgreSQL
make start-infra

# Stop local infrastructure
make stop-infra

# Remove all container data
make wipe-infra

# View infrastructure logs
make infra-logs
```

## Architecture Overview

### Project Structure

```
src/app/
├── config/           # Configuration management
├── db/              # Database models and migrations
├── domain/          # Business logic (DDD)
│   ├── accounts/    # User management & auth
│   ├── todo/        # Todo CRUD & business rules
│   ├── todo_agents/ # AI agent integration
│   ├── agent_sessions/ # Chat session management
│   ├── quota/       # Usage tracking
│   └── system/      # Health checks & utilities
├── lib/             # Shared utilities
└── server/          # Application configuration
```

### Key Architectural Patterns

1. **Domain-Driven Design**: Business logic organized in domain modules
2. **Clean Architecture**: Clear separation of concerns with dependency injection
3. **Repository Pattern**: Data access through Advanced Alchemy repositories
4. **Service Layer**: Business logic encapsulated in service classes
5. **Async/Await**: Non-blocking I/O throughout the application

### AI Integration Architecture

The AI agent system consists of:
- **OpenAI Agents SDK**: Core agent framework
- **Tool System**: Extensible tool definitions for todo operations
- **Session Management**: Persistent conversation history
- **Streaming Support**: Real-time agent responses via SSE
- **Context Management**: User-scoped agent context and data access

## Testing

### Running Tests

```bash
# Run unit tests
make test

# Run integration tests
uv run pytest tests/integration

# Run tests with coverage
make coverage

# Run all tests including custom markers
make test-all
```

### Test Structure

- **Unit Tests**: `tests/unit/` - Test individual components in isolation
- **Integration Tests**: `tests/integration/` - Test API endpoints and workflows
- **Fixtures**: `tests/fixtures/` - Test data and helper functions

### Writing Tests

The project uses pytest with AsyncIO support:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_todo(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/todos",
        json={"title": "Test Todo"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Todo"
```

## Configuration

### Environment Variables

Key configuration options (see `.env.local.example` for complete list):

```bash
# Application
SECRET_KEY                    # JWT signing key
LITESTAR_DEBUG               # Debug mode
LITESTAR_HOST                # Server host
LITESTAR_PORT                # Server port

# Database
DATABASE_URL                 # PostgreSQL connection string
DATABASE_POOL_SIZE           # Database connection pool size
DATABASE_ECHO               # Enable query logging

# AI Services
VOLCENGINE_API_KEY          # VolcEngine API key
VOLCENGINE_BASE_URL         # VolcEngine API endpoint
GLM_API_KEY                 # GLM model API key
GLM_BASE_URL               # GLM model endpoint

# Email
SMTP_USERNAME               # SMTP username
SMTP_PASSWORD               # SMTP password
SMTP_HOST                   # SMTP server
SMTP_PORT                   # SMTP port

# Storage (S3)
S3_ACCESS_KEY              # S3 access key
S3_SECRET_KEY              # S3 secret key
S3_BUCKET_NAME             # S3 bucket name
S3_ENDPOINT_URL            # S3 endpoint
```

### Configuration Classes

The application uses typed configuration classes:

- **AppSettings**: Application-level configuration
- **DatabaseSettings**: Database connection settings
- **AISettings**: AI provider configuration
- **SMTPSettings**: Email service configuration

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Ensure PostgreSQL is running
   make start-infra

   # Check connection details in .env.local
   # Verify DATABASE_URL matches docker-compose configuration
   ```

2. **Migration Issues**
   ```bash
   # Reset database completely
   make wipe-infra
   make start-infra
   uv run app database upgrade
   ```

3. **Import Errors**
   ```bash
   # Ensure virtual environment is activated
   # Reinstall dependencies
   make install
   ```

4. **Permission Issues**
   ```bash
   # Fix file permissions
   chmod +x scripts/*.sh
   ```

### Debug Mode

Enable debug logging by setting in `.env.local`:

```bash
LITESTAR_DEBUG=true
LOG_LEVEL=10
DATABASE_ECHO=true
```

### Health Checks

Monitor application health:

```bash
curl http://localhost:8089/health
```

### Getting Help

- Check the application logs for detailed error messages
- Review the configuration in `.env.local`
- Consult the API documentation at `/schema`
- Check the test files for usage examples

## Next Steps

Now that you have the application running, here are some suggested next steps:

### For Developers

1. **Explore the Codebase**
   - Read the domain logic in `src/app/domain/`
   - Examine the API controllers
   - Review the database models in `src/app/db/`

2. **Contribute to the Project**
   - Set up pre-commit hooks: `uv run pre-commit install`
   - Run the full test suite: `make check-all`
   - Check the contribution guidelines

3. **Extend Functionality**
   - Add new AI tools to the agent system
   - Implement additional todo features
   - Create new API endpoints
   - Add custom authentication providers

### For Users

1. **Explore the AI Agent Features**
   - Try natural language todo creation
   - Use the agent for scheduling and time management
   - Experiment with complex queries and requests

2. **API Integration**
   - Use the OpenAPI documentation at `/schema`
   - Test endpoints with tools like Postman or curl
   - Implement client applications

3. **Advanced Configuration**
   - Set up email notifications
   - Configure external AI providers
   - Set up S3 storage for file uploads

### Additional Resources

- **API Documentation**: Available at http://localhost:8089/schema when the server is running
- **Project Wiki**: See `docs/WIKI_TOC.md` for comprehensive documentation
- **OpenAI Agents SDK**: https://github.com/openai/openai-agents-sdk
- **Litestar Documentation**: https://docs.litestar.dev/

---

## Support

If you encounter any issues or have questions:

1. Check this guide and the existing documentation
2. Review the test files for usage examples
3. Check the GitHub issues (if applicable)
4. Enable debug mode to get detailed logging

Happy coding! 🚀