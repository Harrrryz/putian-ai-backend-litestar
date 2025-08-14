# Domain Architecture Guide: Adding New Domains

This document provides a comprehensive guide for adding new domains to the Putian AI Todo Backend Litestar project. The project follows a domain-driven design pattern with a clear separation of concerns.

## Overview

The project uses a modular domain architecture where each domain represents a specific business area. Currently, the project has three main domains:

- **accounts**: User management, authentication, and authorization
- **system**: System-level operations like health checks
- **todo**: Todo item management and AI agent integration

## Domain Structure

Each domain follows a consistent file structure and naming convention:

```
src/app/domain/{domain_name}/
├── __init__.py                 # Domain module exports
├── deps.py                     # Dependency injection providers
├── guards.py                   # Security guards and permissions (optional)
├── schemas.py                  # Pydantic models for API serialization
├── services.py                 # Business logic and database operations
├── signals.py                  # Event handlers (optional)
├── urls.py                     # URL pattern constants
├── {special_files}.py          # Domain-specific files (e.g., todo_agents.py)
└── controllers/                # HTTP request handlers
    ├── __init__.py
    └── {resource}.py           # Individual controller files
```

## Step-by-Step Guide to Add a New Domain

### 1. Create Domain Directory Structure

Create the domain directory and basic files:

```powershell
# Create domain directory
mkdir src/app/domain/{domain_name}
mkdir src/app/domain/{domain_name}/controllers

# Create basic files
New-Item src/app/domain/{domain_name}/__init__.py
New-Item src/app/domain/{domain_name}/deps.py
New-Item src/app/domain/{domain_name}/schemas.py
New-Item src/app/domain/{domain_name}/services.py
New-Item src/app/domain/{domain_name}/urls.py
New-Item src/app/domain/{domain_name}/controllers/__init__.py
New-Item src/app/domain/{domain_name}/controllers/{resource}.py
```

### 2. Create Database Models

First, create the database models in `src/app/db/models/`:

```python
# src/app/db/models/{domain_name}.py
from __future__ import annotations

from uuid import UUID
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from advanced_alchemy.base import UUIDAuditBase

class YourModel(UUIDAuditBase):
    """Your model description."""
    
    __tablename__ = "your_table_name"
    
    # Define your columns
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    
    # Define relationships
    user: Mapped[User] = relationship("User", back_populates="your_models")
```

Remember to update `src/app/db/models/__init__.py` to export your new model.

### 3. Define URL Constants

Create URL patterns in `urls.py`:

```python
# src/app/domain/{domain_name}/urls.py
"""URL constants for {domain_name} domain."""

# Base path for the domain
{DOMAIN_NAME}_BASE = "/api/{domain-name}"

# CRUD operations
{DOMAIN_NAME}_LIST = f"{DOMAIN_NAME}_BASE"
{DOMAIN_NAME}_CREATE = f"{DOMAIN_NAME}_BASE"
{DOMAIN_NAME}_DETAIL = f"{DOMAIN_NAME}_BASE/{{item_id:uuid}}"
{DOMAIN_NAME}_UPDATE = f"{DOMAIN_NAME}_BASE/{{item_id:uuid}}"
{DOMAIN_NAME}_DELETE = f"{DOMAIN_NAME}_BASE/{{item_id:uuid}}"

# Add any domain-specific endpoints
{DOMAIN_NAME}_SPECIAL_ACTION = f"{DOMAIN_NAME}_BASE/special-action"
```

### 4. Create Pydantic Schemas

Define API schemas in `schemas.py`:

```python
# src/app/domain/{domain_name}/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.accounts.schemas import PydanticBaseModel

__all__ = (
    "YourModelSchema",
    "YourModelCreate", 
    "YourModelUpdate",
)

class YourModelSchema(PydanticBaseModel):
    """Schema for reading your model."""
    
    id: UUID
    name: str
    description: str | None = None
    user_id: UUID
    created_at: datetime
    updated_at: datetime

class YourModelCreate(PydanticBaseModel):
    """Schema for creating your model."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

class YourModelUpdate(PydanticBaseModel):
    """Schema for updating your model."""
    
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
```

### 5. Implement Services

Create business logic in `services.py`:

```python
# src/app/domain/{domain_name}/services.py
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m

if TYPE_CHECKING:
    pass

class YourModelService(SQLAlchemyAsyncRepositoryService[m.YourModel]):
    """Handles database operations for your model."""

    class Repository(SQLAlchemyAsyncRepository[m.YourModel]):
        """Your model SQLAlchemy Repository."""
        
        model_type = m.YourModel

    repository_type = Repository
    match_fields = ["name"]  # Fields used for conflict detection
    
    async def get_by_user(self, user_id: UUID) -> list[m.YourModel]:
        """Get all items for a specific user."""
        return await self.list(m.YourModel.user_id == user_id)
    
    # Add any domain-specific business logic methods
    async def custom_business_logic(self, data: dict) -> m.YourModel:
        """Implement custom business logic."""
        # Your implementation here
        pass
```

### 6. Create Dependency Providers

Set up dependency injection in `deps.py`:

```python
# src/app/domain/{domain_name}/deps.py
"""Dependency providers for {domain_name} domain."""

from __future__ import annotations

from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domain.{domain_name}.services import YourModelService
from app.lib.deps import create_service_provider

# Create service provider with eager loading
provide_your_model_service = create_service_provider(
    YourModelService,
    load=[
        joinedload(m.YourModel.user, innerjoin=True),
        # Add other relationships to eager load
    ],
    error_messages={
        "duplicate_key": "This item already exists.",
        "integrity": "Operation failed.",
    },
)
```

### 7. Implement Controllers

Create HTTP handlers in `controllers/{resource}.py`:

```python
# src/app/domain/{domain_name}/controllers/{resource}.py
"""Controllers for {domain_name} domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from litestar import Controller, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Dependency, Parameter

from app.domain.{domain_name} import urls
from app.domain.{domain_name}.deps import provide_your_model_service
from app.domain.{domain_name}.schemas import (
    YourModelSchema,
    YourModelCreate, 
    YourModelUpdate
)
from app.lib.deps import create_filter_dependencies

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service import OffsetPagination
    from app.domain.{domain_name}.services import YourModelService

class YourModelController(Controller):
    """Controller for your model operations."""
    
    tags = ["{Domain Name}"]
    dependencies = {
        "service": Provide(provide_your_model_service),
    } | create_filter_dependencies(
        {
            "id_filter": UUID,
            "search": "name",  # Searchable fields
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "created_at",
            "sort_order": "desc",
        },
    )
    
    @get(operation_id="List{DomainName}", path=urls.{DOMAIN_NAME}_LIST)
    async def list_items(
        self,
        service: YourModelService,
        filters: Annotated[list[FilterTypes], Dependency(skip_validation=True)],
    ) -> OffsetPagination[YourModelSchema]:
        """List all items with pagination and filtering."""
        results, total = await service.list_and_count(*filters)
        return service.to_schema(
            data=results,
            total=total,
            schema_type=YourModelSchema,
            filters=filters,
        )
    
    @post(operation_id="Create{DomainName}", path=urls.{DOMAIN_NAME}_CREATE)
    async def create_item(
        self,
        service: YourModelService,
        data: YourModelCreate,
    ) -> YourModelSchema:
        """Create a new item."""
        obj = await service.create(data.to_dict())
        return service.to_schema(schema_type=YourModelSchema, data=obj)
    
    @get(operation_id="Get{DomainName}", path=urls.{DOMAIN_NAME}_DETAIL)
    async def get_item(
        self,
        service: YourModelService,
        item_id: UUID = Parameter(title="Item ID", description="The item ID"),
    ) -> YourModelSchema:
        """Get an item by ID."""
        obj = await service.get_one(id=item_id)
        return service.to_schema(schema_type=YourModelSchema, data=obj)
    
    @patch(operation_id="Update{DomainName}", path=urls.{DOMAIN_NAME}_UPDATE)
    async def update_item(
        self,
        service: YourModelService,
        data: YourModelUpdate,
        item_id: UUID = Parameter(title="Item ID", description="The item ID"),
    ) -> YourModelSchema:
        """Update an item."""
        obj = await service.update(item_id, data.to_dict())
        return service.to_schema(schema_type=YourModelSchema, data=obj)
    
    @delete(operation_id="Delete{DomainName}", path=urls.{DOMAIN_NAME}_DELETE)
    async def delete_item(
        self,
        service: YourModelService,
        item_id: UUID = Parameter(title="Item ID", description="The item ID"),
    ) -> None:
        """Delete an item."""
        await service.delete(item_id)
```

### 8. Update Controller Index

Export your controller in `controllers/__init__.py`:

```python
# src/app/domain/{domain_name}/controllers/__init__.py
"""Controllers for {domain_name} domain."""

from .{resource} import YourModelController

__all__ = ("YourModelController",)
```

### 9. Update Domain Index

Export domain components in `__init__.py`:

```python
# src/app/domain/{domain_name}/__init__.py
"""{Domain Name} domain logic."""

from . import controllers, deps, schemas, services, urls

__all__ = ("controllers", "deps", "schemas", "services", "urls")
```

### 10. Register Controllers in Main Application

Update `src/app/server/core.py` to include your new controllers:

```python
# In the imports section
from app.domain.{domain_name}.controllers import YourModelController

# In the route_handlers list
app_config.route_handlers.extend(
    [
        SystemController,
        AccessController,
        UserController,
        UserRoleController,
        TodoController,
        YourModelController,  # Add your new controller
    ],
)
```

### 11. Add Guards (Optional)

If your domain requires specific security guards, create `guards.py`:

```python
# src/app/domain/{domain_name}/guards.py
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.exceptions import PermissionDeniedException

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler

def requires_domain_permission(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Check domain-specific permissions."""
    # Implement your permission logic
    if not connection.user.has_permission("domain_access"):
        raise PermissionDeniedException("Insufficient permissions")
```

### 12. Add Signals (Optional)

For event handling, create `signals.py`:

```python
# src/app/domain/{domain_name}/signals.py
"""Event handlers for {domain_name} domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.events import SimpleEventEmitter

if TYPE_CHECKING:
    pass

async def after_create_handler(data: dict) -> None:
    """Handle post-creation events."""
    # Implement event handling logic
    pass

# Register event handlers
event_emitter = SimpleEventEmitter()
event_emitter.on("after_create", after_create_handler)
```

## Best Practices

### 1. Naming Conventions

- **Domain names**: Use lowercase with underscores (e.g., `user_management`)
- **Model classes**: Use PascalCase (e.g., `UserProfile`)
- **Service classes**: Use PascalCase with "Service" suffix (e.g., `UserProfileService`)
- **Schema classes**: Use PascalCase with descriptive suffix (e.g., `UserProfileCreate`)
- **URL constants**: Use SCREAMING_SNAKE_CASE (e.g., `USER_PROFILE_LIST`)

### 2. Error Handling

Always include proper error messages in service providers:

```python
provide_service = create_service_provider(
    YourService,
    error_messages={
        "duplicate_key": "Specific error message for duplicates",
        "integrity": "Specific error message for integrity violations",
        "not_found": "Specific error message for not found",
    },
)
```

### 3. Database Relationships

When defining relationships, always consider:
- Eager loading in service providers (`joinedload`, `selectinload`)
- Back references in models
- Cascade behaviors for deletions

### 4. Security Considerations

- Use appropriate guards for controllers
- Validate user permissions in services
- Sanitize input data in schemas
- Use dependency injection for user context

### 5. Testing

Create corresponding test files:
- `tests/unit/domain/{domain_name}/test_services.py`
- `tests/integration/test_{domain_name}.py`

### 6. Documentation

- Add comprehensive docstrings to all classes and methods
- Include operation IDs in controller methods
- Document schema fields with descriptions
- Add examples to schema fields where helpful

## Example: Creating a "Projects" Domain

Here's a complete example of adding a "projects" domain:

1. **Database Model** (`src/app/db/models/project.py`):
```python
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from advanced_alchemy.base import UUIDAuditBase

class Project(UUIDAuditBase):
    __tablename__ = "project"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    
    user: Mapped[User] = relationship("User", back_populates="projects")
```

2. **URL Constants** (`src/app/domain/projects/urls.py`):
```python
PROJECT_BASE = "/api/projects"
PROJECT_LIST = f"{PROJECT_BASE}"
PROJECT_CREATE = f"{PROJECT_BASE}"
PROJECT_DETAIL = f"{PROJECT_BASE}/{{project_id:uuid}}"
PROJECT_UPDATE = f"{PROJECT_BASE}/{{project_id:uuid}}"
PROJECT_DELETE = f"{PROJECT_BASE}/{{project_id:uuid}}"
```

3. **Schemas** (`src/app/domain/projects/schemas.py`):
```python
class ProjectSchema(PydanticBaseModel):
    id: UUID
    name: str
    description: str | None = None
    user_id: UUID
    created_at: datetime
    updated_at: datetime

class ProjectCreate(PydanticBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

class ProjectUpdate(PydanticBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
```

Following this guide ensures consistency across the codebase and makes it easier for team members to understand and maintain the application.

## Migration Guide

When adding new domains, remember to:

1. Create database migrations for new models
2. Update API documentation
3. Add integration tests
4. Update deployment configurations if needed
5. Consider backwards compatibility

This architecture promotes maintainability, testability, and clear separation of concerns while following established patterns in the codebase.
