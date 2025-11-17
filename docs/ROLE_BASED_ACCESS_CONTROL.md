# Role-Based Access Control (RBAC) Documentation

This document provides comprehensive documentation for the Role-Based Access Control (RBAC) system implemented in the Todo AI application. The RBAC system is built on Litestar with SQLAlchemy models and provides fine-grained permission management for users and resources.

## Overview

The RBAC system implements a flexible role-based authorization model that allows administrators to:

- Define roles with specific permissions
- Assign multiple roles to users
- Protect API endpoints based on user roles
- Manage role assignments dynamically
- Implement hierarchical access control

## Core Components

### 1. Role Model

The `Role` model defines system roles with unique identifiers and descriptions.

**Location**: `src/app/db/models/role.py`

```python
class Role(UUIDAuditBase, SlugKey):
    """Role model with audit fields and slug-based identification."""

    __tablename__ = "role"

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]

    # Relationships
    users: Mapped[list[UserRole]] = relationship(
        back_populates="role",
        cascade="all, delete",
        lazy="noload",
        viewonly=True,
    )
```

#### Role Fields

- **id**: UUID primary key (inherited from UUIDAuditBase)
- **name**: Unique human-readable role name (e.g., "Application Access", "Superuser")
- **slug**: URL-friendly unique identifier (inherited from SlugKey)
- **description**: Optional role description
- **created_at/updated_at**: Audit timestamps (inherited from UUIDAuditBase)

### 2. User-Role Relationship Model

The `UserRole` model manages many-to-many relationships between users and roles.

**Location**: `src/app/db/models/user_role.py`

```python
class UserRole(UUIDAuditBase):
    """Association table linking users to roles."""

    __tablename__ = "user_account_role"
    __table_args__ = {"comment": "Links a user to a specific role."}

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"), nullable=False)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("role.id", ondelete="cascade"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))

    # Relationships with association proxies
    user: Mapped[User] = relationship(back_populates="roles", innerjoin=True, uselist=False, lazy="joined")
    role: Mapped[Role] = relationship(back_populates="users", innerjoin=True, uselist=False, lazy="joined")

    # Association proxies for convenient access
    user_name: AssociationProxy[str] = association_proxy("user", "name")
    user_email: AssociationProxy[str] = association_proxy("user", "email")
    role_name: AssociationProxy[str] = association_proxy("role", "name")
    role_slug: AssociationProxy[str] = association_proxy("role", "slug")
```

#### UserRole Fields

- **id**: UUID primary key
- **user_id**: Foreign key to User model
- **role_id**: Foreign key to Role model
- **assigned_at**: Timestamp when role was assigned to user
- **created_at/updated_at**: Audit timestamps

### 3. User Model Integration

The `User` model includes role relationships for RBAC functionality.

**Location**: `src/app/db/models/user.py`

```python
class User(UUIDAuditBase):
    """User model with RBAC integration."""

    # ... other fields ...

    # RBAC-related fields
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Role relationships
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        lazy="selectin",
        uselist=True,
        cascade="all, delete",
    )
```

## Default Roles Configuration

The system includes two default roles defined in fixtures:

**Location**: `src/app/db/fixtures/role.json`

```json
[
    {
        "slug": "application-access",
        "name": "Application Access",
        "description": "Default role required for access. This role allows you to query and access the application."
    },
    {
        "slug": "superuser",
        "name": "Superuser",
        "description": "Allows superuser access to the application."
    }
]
```

### Role Hierarchy

1. **Application Access** (`DEFAULT_USER_ROLE`): Basic access for verified users
2. **Superuser** (`SUPERUSER_ACCESS_ROLE`): Full administrative access

## RBAC Services

### 1. RoleService

Handles role management operations.

**Location**: `src/app/domain/accounts/services.py`

```python
class RoleService(SQLAlchemyAsyncRepositoryService[m.Role]):
    """Handles database operations for roles."""

    class Repository(SQLAlchemyAsyncSlugRepository[m.Role]):
        """Role SQLAlchemy Repository with slug support."""
        model_type = m.Role

    repository_type = Repository
    match_fields = ["name"]

    async def to_model_on_create(self, data: ModelDictT[m.Role]) -> ModelDictT[m.Role]:
        data = schema_dump(data)
        if is_dict_without_field(data, "slug"):
            data["slug"] = await self.repository.get_available_slug(data["name"])
        return data
```

### 2. UserRoleService

Manages user-role assignments.

```python
class UserRoleService(SQLAlchemyAsyncRepositoryService[m.UserRole]):
    """Handles database operations for user roles."""

    class Repository(SQLAlchemyAsyncRepository[m.UserRole]):
        """User Role SQLAlchemy Repository."""
        model_type = m.UserRole

    repository_type = Repository
```

### 3. UserService with RBAC Methods

The UserService includes role-checking functionality.

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """User service with RBAC integration."""

    default_role = constants.DEFAULT_USER_ROLE

    @staticmethod
    async def has_role_id(db_obj: m.User, role_id: UUID) -> bool:
        """Check if user has specified role ID."""
        return any(assigned_role.role_id for assigned_role in db_obj.roles if assigned_role.role_id == role_id)

    @staticmethod
    async def has_role(db_obj: m.User, role_name: str) -> bool:
        """Check if user has specified role name."""
        return any(assigned_role.role_name for assigned_role in db_obj.roles if assigned_role.role_name == role_name)

    @staticmethod
    def is_superuser(user: m.User) -> bool:
        """Check if user has superuser privileges."""
        return bool(
            user.is_superuser
            or any(assigned_role.role.name for assigned_role in user.roles if assigned_role.role.name in {"Superuser"}),
        )
```

## Authorization Guards

### 1. Superuser Guard

Restricts access to superusers only.

**Location**: `src/app/domain/accounts/guards.py`

```python
def requires_superuser(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Request requires active superuser."""
    if connection.user.is_superuser:
        return
    raise PermissionDeniedException(detail="Insufficient privileges")
```

### 2. Active User Guard

Ensures user account is active.

```python
def requires_active_user(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Request requires active user."""
    if connection.user.is_active:
        return
    msg = "Inactive account"
    raise PermissionDeniedException(msg)
```

### 3. Verified User Guard

Ensures user email is verified.

```python
def requires_verified_user(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Verify the connection user is verified."""
    if connection.user.is_verified:
        return
    raise PermissionDeniedException(detail="User account is not verified.")
```

## Role Management Controllers

### 1. Role Assignment Controller

Handles role assignment and revocation.

**Location**: `src/app/domain/accounts/controllers/user_role.py`

```python
class UserRoleController(Controller):
    """Handles the adding and removing of User Role records."""

    tags = ["User Account Roles"]
    guards = [requires_superuser]  # Only superusers can manage roles

    @post(operation_id="AssignUserRole", path=urls.ACCOUNT_ASSIGN_ROLE)
    async def assign_role(
        self,
        roles_service: RoleService,
        users_service: UserService,
        user_roles_service: UserRoleService,
        data: schemas.UserRoleAdd,
        role_slug: str = Parameter(title="Role Slug", description="The role to grant."),
    ) -> schemas.Message:
        """Assign a role to a user."""
        role_id = (await roles_service.get_one(slug=role_slug)).id
        user_obj = await users_service.get_one(email=data.user_name)
        obj, created = await user_roles_service.get_or_upsert(role_id=role_id, user_id=user_obj.id)

        if created:
            return schemas.Message(message=f"Successfully assigned the '{obj.role_slug}' role to {obj.user_email}.")
        return schemas.Message(message=f"User {obj.user_email} already has the '{obj.role_slug}' role.")

    @post(operation_id="RevokeUserRole", path=urls.ACCOUNT_REVOKE_ROLE)
    async def revoke_role(
        self,
        users_service: UserService,
        user_roles_service: UserRoleService,
        data: schemas.UserRoleRevoke,
        role_slug: str = Parameter(title="Role Slug", description="The role to revoke."),
    ) -> schemas.Message:
        """Revoke a role from a user."""
        user_obj = await users_service.get_one(email=data.user_name)
        removed_role: bool = False

        for user_role in user_obj.roles:
            if user_role.role_slug == role_slug:
                await user_roles_service.delete(user_role.id)
                removed_role = True

        if not removed_role:
            msg = "User did not have role assigned."
            raise ConflictError(msg)

        return schemas.Message(message=f"Removed the '{role_slug}' role from User {user_obj.email}.")
```

### 2. Role Management Controller

Base controller for role management operations.

**Location**: `src/app/domain/accounts/controllers/roles.py`

```python
class RoleController(Controller):
    """Handles the adding and removing of new Roles."""

    tags = ["Roles"]
    guards = [requires_superuser]  # Only superusers can manage roles
```

## API Endpoints

### Role Assignment Endpoints

- **POST** `/api/roles/{role_slug}/assign` - Assign role to user
- **POST** `/api/roles/{role_slug}/revoke` - Revoke role from user

Both endpoints require:
- Superuser privileges
- User email in request body
- Role slug in URL path

### Example API Usage

#### Assign Role

```bash
curl -X POST "http://localhost:8000/api/roles/superuser/assign" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_name": "user@example.com"}'
```

#### Revoke Role

```bash
curl -X POST "http://localhost:8000/api/roles/superuser/revoke" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_name": "user@example.com"}'
```

## Integration with Authentication

### JWT Token Integration

The RBAC system integrates with JWT authentication through the `current_user_from_token` function:

```python
async def current_user_from_token(token: Token, connection: ASGIConnection[Any, Any, Any, Any]) -> m.User | None:
    """Lookup current user from local JWT token."""
    service = await anext(provide_users_service(alchemy.provide_session(connection.app.state, connection.scope)))
    user = await service.get_one_or_none(email=token.sub)
    return user if user and user.is_active and user.is_verified else None
```

### User Registration with Default Role

New users automatically receive the default role during registration:

```python
@post(operation_id="AccountRegister", path=urls.ACCOUNT_REGISTER)
async def signup(self, request: Request, users_service: UserService, roles_service: RoleService, data: AccountRegister) -> User:
    """User Signup with automatic role assignment."""
    user_data = data.to_dict()

    # Add default role
    role_obj = await roles_service.get_one_or_none(slug=slugify(users_service.default_role))
    if role_obj is not None:
        user_data.update({"role_id": role_obj.id})

    # Create user with role
    user = await users_service.create(user_data)
    return users_service.to_schema(user, schema_type=User)
```

## Database Schema

### Role Table

```sql
CREATE TABLE role (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL UNIQUE,
    slug VARCHAR NOT NULL UNIQUE,
    description VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### User-Role Association Table

```sql
CREATE TABLE user_account_role (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);
```

## CLI Commands for Role Management

### Create Default Roles

```bash
uv run app users create-roles
```

This command:
- Loads role fixtures from `src/app/db/fixtures/role.json`
- Creates missing roles in the database
- Assigns default role to all active users who don't have it

### Promote User to Superuser

```bash
uv run app user promote --email admin@example.com
```

### Create Superuser

```bash
uv run app user create --email admin@example.com --name "Admin User" --password secure_password --superuser
```

## Security Considerations

### 1. Guard Implementation

- All role management endpoints are protected by `requires_superuser` guard
- Guards are evaluated before controller methods execute
- Failed authorization results in `PermissionDeniedException`

### 2. Cascade Operations

- Role deletions cascade to user-role assignments
- User deletions cascade to role assignments
- Maintains referential integrity

### 3. Audit Trail

- All role assignments include `assigned_at` timestamps
- UUID primary keys prevent enumeration attacks
- Full audit trails with `created_at`/`updated_at` fields

### 4. Input Validation

- Role slugs are validated and auto-generated from names
- Email validation for user identification
- Type-safe UUID foreign keys

## Best Practices

### 1. Role Assignment

```python
# Good: Use service methods for role checking
if await UserService.has_role(user, "Superuser"):
    # Grant access
    pass

# Good: Use built-in superuser check
if UserService.is_superuser(user):
    # Grant admin access
    pass
```

### 2. Guard Composition

```python
# Good: Multiple guards for layered security
guards = [requires_active_user, requires_verified_user]

# Good: Role-specific guards
guards = [requires_superuser]
```

### 3. Error Handling

```python
# Good: Graceful handling of missing roles
role_obj = await roles_service.get_one_or_none(slug=role_slug)
if role_obj is None:
    raise NotFoundException(detail=f"Role '{role_slug}' not found")
```

### 4. Database Queries

```python
# Good: Use association proxies for efficient queries
user_roles = await user_roles_service.list(user_id=user.id)
role_names = [ur.role_name for ur in user_roles]

# Good: Eager loading for performance
user = await users_service.get_one(
    id=user_id,
    load_options=[
        selectinload(m.User.roles).options(
            joinedload(m.UserRole.role, innerjoin=True)
        )
    ]
)
```

## Migration Support

### Initial Migration

**Location**: `src/app/db/migrations/versions/2025-05-23_init_user_and_role_b6185fb1f227.py`

The initial migration creates:
- `user_account` table with `is_superuser` field
- `role` table with slug support
- `user_account_role` association table

### Role Data Migration

```bash
# Load role fixtures
uv run app users create-roles

# Verify role creation
SELECT * FROM role;
```

## Testing Considerations

### Unit Tests

Test role checking logic:

```python
async def test_user_has_role(user_service, test_user):
    # Create role
    role = await role_service.create({"name": "Test Role", "description": "Test"})

    # Assign role to user
    await user_role_service.create({"user_id": test_user.id, "role_id": role.id})

    # Check role assignment
    assert await UserService.has_role(test_user, "Test Role")
```

### Integration Tests

Test API endpoint protection:

```python
async def test_role_assignment_endpoint(client, superuser_token, test_user):
    response = await client.post(
        "/api/roles/application-access/assign",
        json={"user_name": test_user.email},
        headers={"Authorization": f"Bearer {superuser_token}"}
    )
    assert response.status_code == 200
```

### Security Tests

Test unauthorized access:

```python
async def test_unauthorized_role_assignment(client, regular_user_token):
    response = await client.post(
        "/api/roles/superuser/assign",
        json={"user_name": "test@example.com"},
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response.status_code == 403
```

## Performance Optimization

### Database Indexes

The schema includes optimal indexes:
- Unique index on `role.name`
- Unique index on `role.slug`
- Composite unique index on `user_account_role(user_id, role_id)`
- Foreign key indexes for join performance

### Query Optimization

```python
# Efficient role checking with association proxies
user_roles = await user_roles_service.list(user_id=user.id)
has_role = any(ur.role_slug == target_slug for ur in user_roles)

# Efficient bulk operations
await role_service.upsert_many(match_fields=["name"], data=role_data)
```

### Caching Considerations

- Role assignments are frequently accessed during authorization
- Consider caching user roles for session duration
- Implement cache invalidation on role assignment changes

## Extending the RBAC System

### Adding New Roles

1. Update role fixtures:
```json
{
    "slug": "content-manager",
    "name": "Content Manager",
    "description": "Can manage content but not user accounts"
}
```

2. Load new roles:
```bash
uv run app users create-roles
```

### Custom Guards

Create role-specific guards:

```python
def requires_content_manager(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Request requires content manager role."""
    if await UserService.has_role(connection.user, "Content Manager"):
        return
    raise PermissionDeniedException(detail="Content manager privileges required")
```

### Hierarchical Roles

Implement role hierarchy:

```python
ROLE_HIERARCHY = {
    "Superuser": ["Application Access", "Content Manager"],
    "Content Manager": ["Application Access"],
}

async def has_role_with_hierarchy(user: m.User, required_role: str) -> bool:
    """Check role with hierarchical inheritance."""
    if await UserService.has_role(user, required_role):
        return True

    user_roles = [ur.role_name for ur in user.roles]
    for role in user_roles:
        if required_role in ROLE_HIERARCHY.get(role, []):
            return True

    return False
```

This comprehensive RBAC system provides a solid foundation for access control in the Todo AI application, with flexibility for future enhancements and role-based security requirements.