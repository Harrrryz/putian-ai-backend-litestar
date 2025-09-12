# Models Extension Guide

This guide provides comprehensive instructions for extending the database models in the Putian AI Todo Backend project built with Litestar and SQLAlchemy.

## Table of Contents

1. [Project Model Architecture](#project-model-architecture)
2. [Base Model Patterns](#base-model-patterns)
3. [Existing Models Overview](#existing-models-overview)
4. [Creating New Models](#creating-new-models)
5. [Model Relationships](#model-relationships)
6. [Advanced Patterns](#advanced-patterns)
7. [Migration Management](#migration-management)
8. [Best Practices](#best-practices)
9. [Common Examples](#common-examples)

## Project Model Architecture

This project uses the following technology stack for data modeling:

- **SQLAlchemy 2.x** with declarative mapping
- **Advanced Alchemy** for enhanced ORM features
- **Alembic** for database migrations
- **UUID-based** primary keys for all models
- **Audit tracking** (created_at, updated_at) built into base models

### Model Location Structure

```
src/app/db/models/
├── __init__.py              # Model exports
├── importance.py            # Enum definitions
├── user.py                  # User model
├── role.py                  # Role model
├── oauth_account.py         # OAuth integration
├── todo.py                  # Todo items
├── tag.py                   # Todo tags
├── todo_tag.py             # Many-to-many association
└── user_role.py            # Many-to-many association
```

## Base Model Patterns

### UUIDAuditBase

All models inherit from `UUIDAuditBase` which provides:

```python
from advanced_alchemy.base import UUIDAuditBase

class YourModel(UUIDAuditBase):
    __tablename__ = "your_table_name"
    # Your fields here
```

**Features provided by UUIDAuditBase:**
- `id`: UUID primary key
- `created_at`: Automatic timestamp on creation
- `updated_at`: Automatic timestamp on updates
- `sa_orm_sentinel`: SQLAlchemy internal field

### Required Imports Pattern

Always use this import pattern for new models:

```python
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, ForeignKey  # Add specific types needed
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .other_model import OtherModel  # Import related models here
```

## Existing Models Overview

### Core Models

#### User Model (`user.py`)
- **Purpose**: Application user accounts
- **Key Features**: 
  - Email-based authentication
  - OAuth integration support
  - Role-based access control
  - Password hashing support
  - Profile information (name, avatar)
  - Activity tracking (login count, verification status)

```python
class User(UUIDAuditBase):
    __tablename__ = "user_account"
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True, default=None)
    # ... other fields
```

#### Todo Model (`todo.py`)
- **Purpose**: Main todo items
- **Key Features**: 
  - Time-based scheduling (start_time, end_time, alarm_time)
  - Importance levels (enum)
  - User ownership
  - Tag association via many-to-many relationship

#### Role Model (`role.py`)
- **Purpose**: User permission roles
- **Key Features**: 
  - Slug-based identification
  - Many-to-many with users
  - Uses `SlugKey` mixin

#### Tag Model (`tag.py`)
- **Purpose**: Todo categorization
- **Key Features**: 
  - User-specific tags
  - Color coding
  - Many-to-many with todos

### Association Models

#### UserRole (`user_role.py`)
- Links users to roles with metadata (assigned_at)
- Uses association proxies for convenient access

#### TodoTag (`todo_tag.py`)  
- Links todos to tags
- Provides association proxies for tag properties

## Creating New Models

### Step 1: Define the Model Class

Create a new file in `src/app/db/models/your_model.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .user import User

class YourModel(UUIDAuditBase):
    """Your model description."""
    
    __tablename__ = "your_table_name"
    __table_args__ = {"comment": "Description of your table"}
    __pii_columns__ = {"field1", "field2"}  # For PII data protection
    
    # Define your fields
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="your_models", lazy="joined")
```

### Step 2: Update Related Models

If your model relates to existing models, update their relationship declarations:

```python
# In user.py, add:
your_models: Mapped[list[YourModel]] = relationship(
    back_populates="user",
    lazy="selectin",
    cascade="all, delete-orphan"
)
```

### Step 3: Update Model Exports

Add your model to `src/app/db/models/__init__.py`:

```python
from .your_model import YourModel

__all__ = (
    # ... existing models
    "YourModel",
)
```

### Step 4: Generate Migration

```bash
# Generate migration
python manage.py database create-migration --description "add your model"

# Review the generated migration file in src/app/db/migrations/versions/

# Apply migration
python manage.py database upgrade
```

## Model Relationships

### One-to-Many Relationships

```python
# Parent Model
class Parent(UUIDAuditBase):
    __tablename__ = "parent"
    name: Mapped[str] = mapped_column(String(100))
    
    children: Mapped[list[Child]] = relationship(
        back_populates="parent",
        lazy="selectin",  # or "noload", "joined"
        cascade="all, delete-orphan"
    )

# Child Model  
class Child(UUIDAuditBase):
    __tablename__ = "child"
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[UUID] = mapped_column(ForeignKey("parent.id"))
    
    parent: Mapped[Parent] = relationship(
        back_populates="children",
        lazy="joined"
    )
```

### Many-to-Many Relationships

Use association objects for rich many-to-many relationships:

```python
# Association Object
class ModelAModelB(UUIDAuditBase):
    __tablename__ = "model_a_model_b"
    model_a_id: Mapped[UUID] = mapped_column(ForeignKey("model_a.id"))
    model_b_id: Mapped[UUID] = mapped_column(ForeignKey("model_b.id"))
    # Additional metadata fields
    relationship_type: Mapped[str] = mapped_column(String(50))
    
    model_a: Mapped[ModelA] = relationship(back_populates="model_b_associations")
    model_b: Mapped[ModelB] = relationship(back_populates="model_a_associations")

# Main Models
class ModelA(UUIDAuditBase):
    __tablename__ = "model_a"
    name: Mapped[str] = mapped_column(String(100))
    
    model_b_associations: Mapped[list[ModelAModelB]] = relationship(
        back_populates="model_a",
        cascade="all, delete-orphan"
    )
    
    # Association proxy for convenient access
    model_bs: AssociationProxy[list[ModelB]] = association_proxy(
        "model_b_associations", "model_b"
    )
```

### Self-Referential Relationships

```python
class Category(UUIDAuditBase):
    __tablename__ = "category"
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("category.id"))
    
    parent: Mapped[Category | None] = relationship(
        "Category",
        back_populates="children",
        remote_side="Category.id"
    )
    children: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="parent"
    )
```

## Advanced Patterns

### Enums

Create enums in separate files for reusability:

```python
# models/status.py
import enum

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# In your model
from sqlalchemy import Enum
from .status import TaskStatus

class Task(UUIDAuditBase):
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum", native_enum=False),
        default=TaskStatus.PENDING
    )
```

### Hybrid Properties

```python
from sqlalchemy.ext.hybrid import hybrid_property

class User(UUIDAuditBase):
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    
    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
```

### Association Proxies

```python
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy

class Todo(UUIDAuditBase):
    # ... other fields
    
    todo_tags: Mapped[list[TodoTag]] = relationship(
        back_populates="todo",
        cascade="all, delete-orphan"
    )
    
    # Convenient access to related objects
    tags: AssociationProxy[list[Tag]] = association_proxy("todo_tags", "tag")
    tag_names: AssociationProxy[list[str]] = association_proxy("todo_tags", "tag_name")
```

### Custom Column Types

```python
from sqlalchemy import TypeDecorator, String
import json

class JSONType(TypeDecorator):
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value

# Usage in model
class Settings(UUIDAuditBase):
    preferences: Mapped[dict] = mapped_column(JSONType(1024))
```

## Migration Management

### Creating Migrations

```bash
# Auto-generate migration from model changes
python manage.py database create-migration --description "descriptive message"

# Create empty migration for custom changes
python manage.py database create-migration --description "custom changes" --empty
```

### Migration Best Practices

1. **Always review generated migrations** before applying
2. **Use descriptive names** for migrations
3. **Test migrations** on development data first
4. **Handle data migration** separately for complex changes

### Sample Migration Structure

```python
"""Add user preferences

Revision ID: abc123
Revises: def456
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Schema changes
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('theme', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_account.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Data migration (if needed)
    # op.execute("INSERT INTO user_preferences ...")

def downgrade() -> None:
    op.drop_table('user_preferences')
```

## Best Practices

### Naming Conventions

- **Table names**: Use snake_case (e.g., `user_account`, `todo_tag`)
- **Column names**: Use snake_case (e.g., `created_at`, `user_id`)
- **Class names**: Use PascalCase (e.g., `UserAccount`, `TodoTag`)
- **Relationship names**: Use descriptive names (e.g., `user_roles`, `todo_tags`)

### Performance Considerations

1. **Use appropriate lazy loading**:
   - `"selectin"`: For collections that are usually accessed
   - `"joined"`: For single objects frequently accessed
   - `"noload"`: For rarely accessed relationships

2. **Add indexes** for frequently queried columns:
   ```python
   email: Mapped[str] = mapped_column(String(255), index=True, unique=True)
   ```

3. **Use appropriate cascade options**:
   - `"all, delete-orphan"`: For owned relationships
   - `"save-update"`: For independent entities

### Security Considerations

1. **Mark PII columns**:
   ```python
   __pii_columns__ = {"email", "name", "phone"}
   ```

2. **Use appropriate nullable settings**:
   ```python
   email: Mapped[str] = mapped_column(nullable=False)  # Required
   phone: Mapped[str | None] = mapped_column(nullable=True)  # Optional
   ```

3. **Set proper foreign key constraints**:
   ```python
   user_id: Mapped[UUID] = mapped_column(
       ForeignKey("user_account.id", ondelete="CASCADE")
   )
   ```

## Common Examples

### Example 1: Adding a Comment System

```python
# models/comment.py
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .user import User
    from .todo import Todo

class Comment(UUIDAuditBase):
    """Comments on todo items."""
    
    __tablename__ = "comment"
    __table_args__ = {"comment": "Comments on todo items"}
    __pii_columns__ = {"content"}
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    todo_id: Mapped[UUID] = mapped_column(
        ForeignKey("todo.id", ondelete="CASCADE"), 
        nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Relationships
    todo: Mapped[Todo] = relationship(
        back_populates="comments",
        lazy="joined"
    )
    author: Mapped[User] = relationship(
        back_populates="comments",
        lazy="joined"
    )

# Update todo.py to add:
comments: Mapped[list[Comment]] = relationship(
    back_populates="todo",
    lazy="selectin",
    cascade="all, delete-orphan"
)

# Update user.py to add:
comments: Mapped[list[Comment]] = relationship(
    back_populates="author",
    lazy="noload"
)
```

### Example 2: Adding File Attachments

```python
# models/attachment.py
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .todo import Todo
    from .user import User

class Attachment(UUIDAuditBase):
    """File attachments for todos."""
    
    __tablename__ = "attachment"
    __table_args__ = {"comment": "File attachments"}
    __pii_columns__ = {"original_filename", "file_path"}
    
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    todo_id: Mapped[UUID] = mapped_column(
        ForeignKey("todo.id", ondelete="CASCADE"),
        nullable=False
    )
    uploaded_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Relationships
    todo: Mapped[Todo] = relationship(
        back_populates="attachments",
        lazy="joined"
    )
    uploaded_by: Mapped[User] = relationship(
        lazy="joined"
    )
```

### Example 3: Adding Soft Delete

```python
from datetime import datetime
from sqlalchemy import DateTime

class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, 
        nullable=True, 
        default=None
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

class YourModel(UUIDAuditBase, SoftDeleteMixin):
    # Your model implementation
    pass
```

## Conclusion

This guide covers the essential patterns and practices for extending models in the Putian AI Todo Backend project. Remember to:

1. Follow the established patterns and conventions
2. Always generate and review migrations
3. Consider performance and security implications
4. Update related models and exports
5. Test your changes thoroughly

For more complex scenarios, refer to the SQLAlchemy and Advanced Alchemy documentation, and consider discussing with the team before implementing major architectural changes.
