# Authorization Guards & Middleware Documentation

This document provides comprehensive documentation for the authorization guards and middleware system implemented in the Todo AI application. The authorization system is built on Litestar's guard architecture with JWT-based authentication and role-based access control (RBAC).

## Table of Contents

1. [Guard Architecture Overview](#guard-architecture-overview)
2. [Authentication Guards](#authentication-guards)
3. [Authorization Middleware Implementation](#authorization-middleware-implementation)
4. [Role-Based Access Control Guards](#role-based-access-control-guards)
5. [Permission Checking and Validation Flows](#permission-checking-and-validation-flows)
6. [Custom Guard Creation and Extension](#custom-guard-creation-and-extension)
7. [Guard Composition and Chaining Patterns](#guard-composition-and-chaining-patterns)
8. [Performance Optimization for Guards](#performance-optimization-for-guards)
9. [Error Handling for Unauthorized Access](#error-handling-for-unauthorized-access)
10. [Testing and Debugging Strategies for Guards](#testing-and-debugging-strategies-for-guards)

## Guard Architecture Overview

The authorization system follows Litestar's guard-based architecture where guards are callable objects that receive request context and route handler information, then either allow the request to proceed or raise an authorization exception.

### Core Architecture Components

```
Request → Middleware → Guards → Controller → Response
           ↓              ↓           ↓
    Logging &       Permission   Business Logic
    Exception       Validation
    Handling        & Role Check
```

### Key Files and Structure

- **`src/app/domain/accounts/guards.py`** - Core guard implementations
- **`src/app/lib/exceptions.py`** - Authorization exception handling
- **`src/app/config/app.py`** - Authentication configuration
- **`src/app/server/core.py`** - Application-level guard registration

### Guard Function Signature

All guards follow the Litestar guard interface:

```python
from typing import TYPE_CHECKING
from litestar.exceptions import PermissionDeniedException

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler

def example_guard(
    connection: ASGIConnection,
    route_handler: BaseRouteHandler
) -> None:
    """Guard implementation."""
    # Check authorization conditions
    if not authorized:
        raise PermissionDeniedException(detail="Access denied")
    # Return None to allow access
```

## Authentication Guards

The system includes three core authentication guards that validate user status and privileges.

### 1. Active User Guard

**Location**: `src/app/domain/accounts/guards.py:28`

```python
def requires_active_user(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Request requires active user.

    Verifies the request user is active.

    Args:
        connection (ASGIConnection): HTTP Request
        _ (BaseRouteHandler): Route handler

    Raises:
        PermissionDeniedException: Permission denied exception
    """
    if connection.user.is_active:
        return
    msg = "Inactive account"
    raise PermissionDeniedException(msg)
```

**Usage Examples**:

```python
# Controller-level application
class UserController(Controller):
    guards = [requires_active_user]

    @get("/profile")
    async def get_profile(self, current_user: m.User) -> User:
        return current_user

# Route-level application
@get("/user/settings", guards=[requires_active_user])
async def get_settings(self, current_user: m.User) -> dict:
    return {"settings": "user_settings"}
```

### 2. Superuser Guard

**Location**: `src/app/domain/accounts/guards.py:46`

```python
def requires_superuser(
    connection: ASGIConnection[m.User, Any, Any, Any],
    _: BaseRouteHandler
) -> None:
    """Request requires active superuser.

    Args:
        connection (ASGIConnection): HTTP Request
        _ (BaseRouteHandler): Route handler

    Raises:
        PermissionDeniedException: Permission denied exception

    Returns:
        None: Returns None when successful
    """
    if connection.user.is_superuser:
        return
    raise PermissionDeniedException(detail="Insufficient privileges")
```

**Usage Examples**:

```python
class AdminController(Controller):
    """Controller for administrative operations."""
    tags = ["Administration"]
    guards = [requires_superuser]  # All endpoints require superuser

    @delete("/users/{user_id}")
    async def delete_user(self, user_id: UUID) -> None:
        """Delete user account - admin only."""
        pass

    @get("/system/stats")
    async def get_system_stats(self) -> dict:
        """Get system statistics - admin only."""
        return {"users": 100, "todos": 1000}
```

### 3. Verified User Guard

**Location**: `src/app/domain/accounts/guards.py:64`

```python
def requires_verified_user(
    connection: ASGIConnection[m.User, Any, Any, Any],
    _: BaseRouteHandler
) -> None:
    """Verify the connection user is verified.

    Args:
        connection (ASGIConnection): Request/Connection object.
        _ (BaseRouteHandler): Route handler.

    Raises:
        PermissionDeniedException: Not authorized

    Returns:
        None: Returns None when successful
    """
    if connection.user.is_verified:
        return
    raise PermissionDeniedException(detail="User account is not verified.")
```

**Usage Examples**:

```python
@post("/todos", guards=[requires_verified_user])
async def create_todo(self, data: TodoCreate) -> Todo:
    """Create a new todo - requires verified email."""
    pass

@get("/protected-feature", guards=[requires_verified_user])
async def protected_feature(self) -> dict:
    """Access to premium features."""
    return {"message": "Premium feature access granted"}
```

## Authorization Middleware Implementation

### JWT Authentication Middleware

The JWT authentication is implemented using Litestar's `OAuth2PasswordBearerAuth`:

**Location**: `src/app/domain/accounts/guards.py:101`

```python
auth = OAuth2PasswordBearerAuth[m.User](
    retrieve_user_handler=current_user_from_token,
    token_secret=settings.app.SECRET_KEY,
    token_url=urls.ACCOUNT_LOGIN,
    exclude=[
        constants.HEALTH_ENDPOINT,
        urls.ACCOUNT_LOGIN,
        urls.ACCOUNT_REGISTER,
        urls.ACCOUNT_VERIFY_EMAIL,
        urls.ACCOUNT_RESEND_VERIFICATION,
        "^/schema",
        "^/public/",
    ],
)
```

### User Retrieval Handler

**Location**: `src/app/domain/accounts/guards.py:82`

```python
async def current_user_from_token(
    token: Token,
    connection: ASGIConnection[Any, Any, Any, Any]
) -> m.User | None:
    """Lookup current user from local JWT token.

    Fetches the user information from the database

    Args:
        token (str): JWT Token Object
        connection (ASGIConnection[Any, Any, Any, Any]): ASGI connection.

    Returns:
        User: User record mapped to the JWT identifier if user exists, is active, and is verified
    """
    service = await anext(provide_users_service(alchemy.provide_session(connection.app.state, connection.scope)))
    user = await service.get_one_or_none(email=token.sub)
    return user if user and user.is_active and user.is_verified else None
```

### Middleware Configuration

The authentication middleware is configured in the application core:

**Location**: `src/app/server/core.py:90`

```python
class ApplicationCore(InitPluginProtocol, CLIPluginProtocol):
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        # ... other configuration ...

        # jwt auth (updates openapi config)
        app_config = jwt_auth.on_app_init(app_config)

        # ... rest of configuration ...
```

### Application-Level Exception Handling

**Location**: `src/app/server/core.py:139`

```python
app_config.exception_handlers = {
    ApplicationError: exception_to_http_response,
    RepositoryError: exception_to_http_response,
}
```

## Role-Based Access Control Guards

The RBAC system provides role-based authorization through custom guards that check user roles and permissions.

### User Service Role Checking

**Location**: `src/app/domain/accounts/services.py`

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """User service with RBAC integration."""

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

### Role-Specific Guard Examples

```python
from app.domain.accounts.services import UserService

def requires_content_manager(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Request requires content manager role."""
    if await UserService.has_role(connection.user, "Content Manager"):
        return
    raise PermissionDeniedException(detail="Content manager privileges required")

def requires_application_access(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Request requires application access role."""
    if await UserService.has_role(connection.user, "Application Access"):
        return
    raise PermissionDeniedException(detail="Application access required")

# Hierarchical role guard
def requires_admin_or_content_manager(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Request requires admin or content manager privileges."""
    if (UserService.is_superuser(connection.user) or
        await UserService.has_role(connection.user, "Content Manager")):
        return
    raise PermissionDeniedException(detail="Admin or content manager privileges required")
```

### Guard Registration in Controllers

**Location**: `src/app/domain/accounts/controllers/user_role.py`

```python
class UserRoleController(Controller):
    """Handles the adding and removing of User Role records."""

    tags = ["User Account Roles"]
    guards = [requires_superuser]  # Only superusers can manage roles

    dependencies = {
        "user_roles_service": Provide(create_service_provider(UserRoleService)),
        "roles_service": Provide(create_service_provider(RoleService)),
        "users_service": Provide(provide_users_service),
    }
```

## Permission Checking and Validation Flows

### Authorization Flow Sequence

```python
# 1. Request arrives at application
# 2. JWT middleware validates token and sets connection.user
# 3. Guards are executed in order of definition
# 4. Each guard validates user permissions
# 5. If all guards pass, controller method executes
# 6. If any guard fails, PermissionDeniedException is raised
```

### Validation Flow Examples

#### Flow 1: Simple Role Check

```python
@get("/admin/dashboard", guards=[requires_superuser])
async def admin_dashboard(self, current_user: m.User) -> dict:
    """
    Validation Flow:
    1. JWT token validated by middleware
    2. current_user injected from token
    3. requires_superuser guard checks connection.user.is_superuser
    4. If True: proceed to method
    5. If False: raise PermissionDeniedException
    """
    return {"admin_data": "sensitive_info"}
```

#### Flow 2: Multi-Guard Chain

```python
@post("/premium-feature", guards=[requires_active_user, requires_verified_user])
async def premium_feature(self, current_user: m.User, data: PremiumRequest) -> dict:
    """
    Validation Flow:
    1. JWT token validated by middleware
    2. requires_active_user checks connection.user.is_active
    3. requires_verified_user checks connection.user.is_verified
    4. Both must pass to proceed to method
    """
    return {"premium_content": "accessible"}
```

#### Flow 3: Role-Based Access

```python
@get("/content/manage", guards=[requires_content_manager])
async def manage_content(self, current_user: m.User) -> list:
    """
    Validation Flow:
    1. JWT token validated by middleware
    2. requires_content_manager guard queries user roles
    3. Checks if "Content Manager" role exists for user
    4. Role check determines access
    """
    return await content_service.get_all_content()
```

### Database Query Optimization

```python
# Efficient role checking with eager loading
async def get_user_with_roles(user_service: UserService, user_id: UUID) -> m.User:
    """Get user with roles eagerly loaded for guard performance."""
    return await user_service.get_one(
        id=user_id,
        load_options=[
            selectinload(m.User.roles).options(
                joinedload(m.UserRole.role, innerjoin=True)
            )
        ]
    )
```

## Custom Guard Creation and Extension

### Guard Creation Pattern

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from litestar.exceptions import PermissionDeniedException

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler

def custom_guard(
    connection: ASGIConnection,
    route_handler: BaseRouteHandler
) -> None:
    """Custom guard implementation."""
    # Implement your authorization logic here
    if not authorized:
        raise PermissionDeniedException(detail="Custom authorization failed")
```

### Time-Based Guard

```python
from datetime import time, datetime

def requires_business_hours(
    connection: ASGIConnection,
    route_handler: BaseRouteHandler
) -> None:
    """Only allow access during business hours (9 AM - 5 PM)."""
    current_time = datetime.now().time()
    if time(9, 0) <= current_time <= time(17, 0):
        return
    raise PermissionDeniedException(detail="Access only allowed during business hours")
```

### Feature Flag Guard

```python
from app.domain.features.services import FeatureFlagService

async def requires_feature_flag(
    flag_name: str,
    connection: ASGIConnection,
    route_handler: BaseRouteHandler
) -> None:
    """Check if feature flag is enabled for user."""
    service = await anext(provide_feature_flag_service(connection))
    if await service.is_enabled(flag_name, connection.user.id):
        return
    raise PermissionDeniedException(detail=f"Feature '{flag_name}' is not enabled")
```

### Usage with Parameters

```python
# Parameterized guard factory
def create_permission_guard(required_permission: str):
    """Create a guard that checks for specific permission."""
    def permission_guard(
        connection: ASGIConnection,
        route_handler: BaseRouteHandler
    ) -> None:
        if has_permission(connection.user, required_permission):
            return
        raise PermissionDeniedException(detail=f"Requires '{required_permission}' permission")
    return permission_guard

# Usage
@get("/sensitive-data", guards=[create_permission_guard("read_sensitive")])
async def get_sensitive_data(self) -> dict:
    return {"data": "sensitive"}
```

### Context-Aware Guard

```python
def resource_owner_guard(
    connection: ASGIConnection,
    route_handler: BaseRouteHandler
) -> None:
    """Only allow resource owners to access their own resources."""
    # Extract resource ID from path parameters
    resource_id = connection.path_params.get("user_id")
    if resource_id and str(connection.user.id) == resource_id:
        return
    raise PermissionDeniedException(detail="Can only access your own resources")
```

### Guard with External Validation

```python
import httpx

async def requires_external_service_validation(
    connection: ASGIConnection,
    route_handler: BaseRouteHandler
) -> None:
    """Validate access through external authorization service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://auth.example.com/validate",
            json={"user_id": str(connection.user.id), "resource": route_handler.path}
        )

    if response.status_code == 200 and response.json().get("allowed"):
        return
    raise PermissionDeniedException(detail="External authorization failed")
```

## Guard Composition and Chaining Patterns

### Sequential Guard Execution

Guards are executed in the order they are defined in the guards list:

```python
# All guards must pass
@get("/secure-endpoint", guards=[
    requires_active_user,      # First: Check user is active
    requires_verified_user,    # Second: Check email is verified
    requires_superuser         # Third: Check superuser status
])
async def secure_endpoint(self) -> dict:
    # Only reached if all guards pass
    return {"data": "highly_sensitive"}
```

### Controller-Level vs Route-Level Guards

```python
class UserController(Controller):
    """User management controller with layered security."""

    # Controller-level guards apply to all routes
    guards = [requires_active_user]

    @get("/profile")
    async def get_profile(self, current_user: m.User) -> User:
        """Uses controller-level guard (active user)."""
        return current_user

    @get("/admin/users", guards=[requires_superuser])
    async def list_users(self) -> list[User]:
        """Combines controller and route-level guards."""
        # Must be active user AND superuser
        pass

    @post("/verify-email", guards=[])  # Override controller guards
    async def verify_email(self) -> dict:
        """No guards required - open endpoint."""
        pass
```

### Conditional Guard Application

```python
def conditional_guards() -> list:
    """Return different guards based on configuration."""
    if settings.app.STRICT_AUTH:
        return [requires_active_user, requires_verified_user]
    return [requires_active_user]

class ConfigurableController(Controller):
    guards = conditional_guards()  # Dynamic guard selection

    @get("/data")
    async def get_data(self) -> dict:
        return {"data": "configurable_access"}
```

### Guard Inheritance Pattern

```python
class BaseController(Controller):
    """Base controller with common guards."""
    guards = [requires_active_user]

class AdminController(BaseController):
    """Admin controller with additional security."""
    guards = [*BaseController.guards, requires_superuser]

    @get("/admin/dashboard")
    async def admin_dashboard(self) -> dict:
        # Requires both active user and superuser
        return {"admin_data": "sensitive"}
```

### Guard Composition Functions

```python
def compose_guards(*guards) -> list:
    """Combine multiple guard lists into one."""
    combined = []
    for guard_list in guards:
        if isinstance(guard_list, list):
            combined.extend(guard_list)
        else:
            combined.append(guard_list)
    return combined

class CompositeController(Controller):
    """Controller using guard composition."""
    guards = compose_guards(
        requires_active_user,
        [requires_verified_user],  # Nested list
        requires_superuser
    )
```

## Performance Optimization for Guards

### Guard Performance Best Practices

#### 1. Minimize Database Queries

```python
# ❌ BAD: Multiple database calls per guard
def requires_multiple_roles_bad(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    user = connection.user
    has_admin = UserService.has_role(user, "Admin")  # DB call
    has_manager = UserService.has_role(user, "Manager")  # DB call
    if not (has_admin or has_manager):
        raise PermissionDeniedException(detail="Insufficient privileges")

# ✅ GOOD: Single query with eager loading
def requires_multiple_roles_good(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    user_roles = [ur.role_name for ur in connection.user.roles]  # Pre-loaded
    if not any(role in user_roles for role in ["Admin", "Manager"]):
        raise PermissionDeniedException(detail="Insufficient privileges")
```

#### 2. Cache Frequently Accessed Permissions

```python
from functools import lru_cache
from typing import Set

@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str) -> Set[str]:
    """Cache user permissions to reduce database calls."""
    # Implementation would cache role-based permissions
    return {"read_todos", "write_todos"}

def cached_permission_guard(required_permission: str):
    """Guard using cached permissions."""
    def guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        permissions = get_user_permissions(str(connection.user.id))
        if required_permission in permissions:
            return
        raise PermissionDeniedException(detail=f"Requires '{required_permission}' permission")
    return guard
```

#### 3. Early Guard Failures

```python
# ✅ GOOD: Check simplest conditions first
def optimized_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Optimized guard with early returns."""
    user = connection.user

    # Check simple boolean first (fastest)
    if not user.is_active:
        raise PermissionDeniedException(detail="Inactive account")

    # Check superuser flag (very fast)
    if user.is_superuser:
        return

    # Check roles only if needed (database query)
    if not any(role.role_name == "Admin" for role in user.roles):
        raise PermissionDeniedException(detail="Admin privileges required")
```

#### 4. Batch Permission Checks

```python
def batch_permission_check(user: m.User, required_permissions: list[str]) -> bool:
    """Check multiple permissions efficiently."""
    user_roles = {role.role_name for role in user.roles}
    user_permissions = set()

    # Map roles to permissions (cached or in-memory)
    role_permissions = {
        "Admin": {"read_all", "write_all", "delete_all"},
        "Manager": {"read_team", "write_team"},
        "User": {"read_own", "write_own"}
    }

    for role in user_roles:
        user_permissions.update(role_permissions.get(role, set()))

    return all(perm in user_permissions for perm in required_permissions)

def requires_multiple_permissions(*permissions):
    """Guard requiring multiple permissions."""
    def guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        if batch_permission_check(connection.user, permissions):
            return
        raise PermissionDeniedException(detail=f"Requires permissions: {', '.join(permissions)}")
    return guard
```

### Database Optimization

#### Optimized User Loading

```python
# In your dependency provider or user retrieval handler
async def provide_user_with_roles(
    connection: ASGIConnection[Any, Any, Any, Any]
) -> m.User:
    """Provide user with roles pre-loaded for guard efficiency."""
    service = await anext(provide_users_service(
        alchemy.provide_session(connection.app.state, connection.scope)
    ))

    # Load user with roles in single query
    return await service.get_one(
        email=connection.user.email if connection.user else None,
        load_options=[
            selectinload(m.User.roles).options(
                joinedload(m.UserRole.role, innerjoin=True)
            )
        ]
    )
```

#### Guard-Aware Repository Queries

```python
class OptimizedUserService(UserService):
    """User service optimized for guard performance."""

    async def get_user_for_guards(self, email: str) -> m.User | None:
        """Get user with all data needed for guards."""
        return await self.get_one_or_none(
            email=email,
            load_options=[
                selectinload(m.User.roles).options(
                    joinedload(m.UserRole.role, innerjoin=True)
                )
            ]
        )

    async def check_all_roles(self, user_id: UUID) -> set[str]:
        """Get all role names for user efficiently."""
        # Single query to get all role names
        result = await self.repository.execute(
            select(m.Role.name)
            .join(m.UserRole)
            .where(m.UserRole.user_id == user_id)
        )
        return {row[0] for row in result}
```

## Error Handling for Unauthorized Access

### Exception Hierarchy

**Location**: `src/app/lib/exceptions.py`

```python
class ApplicationError(Exception):
    """Base exception type for the lib's custom exception types."""
    detail: str

class ApplicationClientError(ApplicationError):
    """Base exception type for client errors."""

class AuthorizationError(ApplicationClientError):
    """A user tried to do something they shouldn't have."""
```

### HTTP Exception Mapping

**Location**: `src/app/lib/exceptions.py:149`

```python
def exception_to_http_response(
    request: Request[Any, Any, Any],
    exc: ApplicationError | RepositoryError,
) -> Response[ExceptionResponseContent]:
    """Transform repository exceptions to HTTP exceptions."""
    http_exc: type[HTTPException]
    if isinstance(exc, NotFoundError):
        http_exc = NotFoundException
    elif isinstance(exc, ConflictError | RepositoryError | IntegrityError):
        http_exc = _HTTPConflictException
    elif isinstance(exc, AuthorizationError):
        http_exc = PermissionDeniedException
    else:
        http_exc = InternalServerException

    if request.app.debug and http_exc not in (PermissionDeniedException, NotFoundError, AuthorizationError):
        return create_debug_response(request, exc)
    return create_exception_response(request, http_exc(detail=str(exc.__cause__)))
```

### Guard Error Patterns

#### 1. Standard Permission Denied

```python
def standard_guard_error(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Standard permission denied with clear message."""
    if not authorized:
        raise PermissionDeniedException(detail="Insufficient privileges")
```

#### 2. Detailed Error Messages

```python
def detailed_guard_error(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Guard with detailed error information."""
    user = connection.user

    if not user.is_active:
        raise PermissionDeniedException(detail="Account is inactive")

    if not user.is_verified:
        raise PermissionDeniedException(detail="Email address not verified")

    if not user.is_superuser:
        user_roles = [role.role_name for role in user.roles]
        raise PermissionDeniedException(
            detail=f"Superuser access required. Current roles: {', '.join(user_roles)}"
        )
```

#### 3. Structured Error Responses

```python
from litestar.response import Response
from litestar.status_codes import HTTP_403_FORBIDDEN

def structured_guard_error(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Guard with structured error response."""
    if not authorized:
        error_data = {
            "error": "authorization_failed",
            "required_role": "admin",
            "user_roles": [role.role_name for role in connection.user.roles],
            "resource": route_handler.path,
            "timestamp": datetime.utcnow().isoformat()
        }
        raise PermissionDeniedException(detail=error_data)
```

### Global Exception Handling

**Location**: `src/app/server/core.py:139`

```python
app_config.exception_handlers = {
    ApplicationError: exception_to_http_response,
    RepositoryError: exception_to_http_response,
    # Additional handlers for specific scenarios
    PermissionDeniedException: custom_permission_handler,
}
```

#### Custom Permission Handler

```python
async def custom_permission_handler(request: Request, exc: PermissionDeniedException) -> Response:
    """Custom handler for permission denied exceptions."""
    response_data = {
        "error": "access_denied",
        "message": str(exc.detail),
        "status": HTTP_403_FORBIDDEN,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Log security events
    logger.warning(
        "access_denied",
        user_id=request.user.id if request.user else None,
        path=request.url.path,
        method=request.method,
        reason=str(exc.detail)
    )

    return Response(
        content=response_data,
        status_code=HTTP_403_FORBIDDEN,
        media_type="application/json"
    )
```

### Security Logging

```python
import structlog

logger = structlog.get_logger()

def security_aware_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Guard with security logging."""
    user = connection.user

    if not authorized:
        # Log security event
        logger.warning(
            "unauthorized_access_attempt",
            user_id=user.id if user else None,
            email=user.email if user else None,
            path=route_handler.path,
            method=connection.method,
            user_agent=connection.headers.get("user-agent"),
            ip_address=connection.client.host if connection.client else None
        )
        raise PermissionDeniedException(detail="Access denied")
```

## Testing and Debugging Strategies for Guards

### Unit Testing Guards

#### Basic Guard Testing

```python
import pytest
from litestar import Request
from litestar.testing import TestClient, create_test_request
from litestar.exceptions import PermissionDeniedException
from app.domain.accounts.guards import requires_active_user, requires_superuser

@pytest.mark.asyncio
async def test_requires_active_user_success():
    """Test requires_active_user guard with active user."""
    # Create mock active user
    user = m.User(is_active=True, is_verified=True, is_superuser=False)

    # Create mock request with user
    request = create_test_request(method="GET", path="/test")
    request._user = user

    # Guard should not raise exception
    requires_active_user(request, None)

@pytest.mark.asyncio
async def test_requires_active_user_failure():
    """Test requires_active_user guard with inactive user."""
    # Create mock inactive user
    user = m.User(is_active=False, is_verified=True, is_superuser=False)

    # Create mock request with user
    request = create_test_request(method="GET", path="/test")
    request._user = user

    # Guard should raise PermissionDeniedException
    with pytest.raises(PermissionDeniedException, match="Inactive account"):
        requires_active_user(request, None)

@pytest.mark.asyncio
async def test_requires_superuser_success():
    """Test requires_superuser guard with superuser."""
    user = m.User(is_active=True, is_verified=True, is_superuser=True)
    request = create_test_request(method="GET", path="/test")
    request._user = user

    # Should not raise exception
    requires_superuser(request, None)

@pytest.mark.asyncio
async def test_requires_superuser_failure():
    """Test requires_superuser guard with regular user."""
    user = m.User(is_active=True, is_verified=True, is_superuser=False)
    request = create_test_request(method="GET", path="/test")
    request._user = user

    with pytest.raises(PermissionDeniedException, match="Insufficient privileges"):
        requires_superuser(request, None)
```

#### Testing Custom Guards

```python
@pytest.mark.asyncio
async def test_role_based_guard():
    """Test role-based guard functionality."""
    # Create user with roles
    admin_role = m.Role(name="Admin", slug="admin")
    user_role = m.Role(name="User", slug="user")

    user = m.User(is_active=True, is_verified=True)
    user.roles = [
        m.UserRole(user=user, role=admin_role),
        m.UserRole(user=user, role=user_role)
    ]

    request = create_test_request(method="GET", path="/test")
    request._user = user

    # Test guard that requires admin role
    def requires_admin_role(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        if any(ur.role.name == "Admin" for ur in connection.user.roles):
            return
        raise PermissionDeniedException(detail="Admin role required")

    # Should not raise exception
    requires_admin_role(request, None)
```

### Integration Testing

#### Testing Guard-Protected Endpoints

```python
from litestar.testing import TestClient
from app.server.app import app

def test_protected_endpoint_with_valid_token(client: TestClient):
    """Test accessing protected endpoint with valid token."""
    # Create and login user
    user_data = {"email": "test@example.com", "password": "securepassword"}
    response = client.post("/api/access/register", json=user_data)
    assert response.status_code == 201

    # Login to get token
    login_response = client.post("/api/access/login", json=user_data)
    token = login_response.json()["access_token"]

    # Access protected endpoint
    response = client.get(
        "/api/access/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_protected_endpoint_without_token(client: TestClient):
    """Test accessing protected endpoint without token."""
    response = client.get("/api/access/profile")
    assert response.status_code == 401  # Unauthorized

def test_admin_endpoint_with_regular_user(client: TestClient):
    """Test accessing admin endpoint with regular user token."""
    # Create regular user
    user_data = {"email": "user@example.com", "password": "password"}
    client.post("/api/access/register", json=user_data)

    # Login
    login_response = client.post("/api/access/login", json=user_data)
    token = login_response.json()["access_token"]

    # Try to access admin endpoint
    response = client.get(
        "/api/accounts/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403  # Forbidden

def test_admin_endpoint_with_superuser(client: TestClient):
    """Test accessing admin endpoint with superuser token."""
    # Create superuser
    admin_data = {"email": "admin@example.com", "password": "adminpassword"}
    client.post("/api/access/register", json=admin_data)

    # Promote to superuser (using CLI or direct database)
    # ... superuser promotion logic ...

    # Login
    login_response = client.post("/api/access/login", json=admin_data)
    token = login_response.json()["access_token"]

    # Access admin endpoint
    response = client.get(
        "/api/accounts/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

### Performance Testing

#### Guard Performance Benchmarking

```python
import time
from typing import Callable

def benchmark_guard(guard: Callable, iterations: int = 1000) -> float:
    """Benchmark guard execution time."""
    user = m.User(is_active=True, is_verified=True, is_superuser=True)
    request = create_test_request(method="GET", path="/test")
    request._user = user

    start_time = time.perf_counter()

    for _ in range(iterations):
        guard(request, None)

    end_time = time.perf_counter()
    return (end_time - start_time) / iterations

def test_guard_performance():
    """Test guard execution performance."""
    # Benchmark different guards
    active_user_time = benchmark_guard(requires_active_user)
    superuser_time = benchmark_guard(requires_superuser)

    print(f"requires_active_user: {active_user_time * 1000:.3f}ms")
    print(f"requires_superuser: {superuser_time * 1000:.3f}ms")

    # Assert reasonable performance (less than 1ms per guard)
    assert active_user_time < 0.001
    assert superuser_time < 0.001
```

### Debugging Guards

#### Guard Debugging Utilities

```python
from functools import wraps

def debug_guard(guard_func):
    """Decorator to add debug logging to guards."""
    @wraps(guard_func)
    async def debug_wrapper(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
        user = getattr(connection, 'user', None)
        user_id = user.id if user else 'anonymous'
        path = route_handler.path if route_handler else 'unknown'

        logger.debug(
            "guard_execution",
            guard_name=guard_func.__name__,
            user_id=user_id,
            path=path,
            method=connection.method
        )

        try:
            result = await guard_func(connection, route_handler)
            logger.debug("guard_passed", guard_name=guard_func.__name__, user_id=user_id)
            return result
        except PermissionDeniedException as e:
            logger.warning(
                "guard_failed",
                guard_name=guard_func.__name__,
                user_id=user_id,
                reason=str(e.detail)
            )
            raise

    return debug_wrapper

# Usage
@debug_guard
def requires_debug_active_user(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Debug version of requires_active_user."""
    return requires_active_user(connection, route_handler)
```

#### Request Inspection

```python
def inspect_request_for_guards(connection: ASGIConnection) -> dict:
    """Inspect request details for guard debugging."""
    return {
        "user_id": getattr(connection.user, 'id', None),
        "user_email": getattr(connection.user, 'email', None),
        "is_active": getattr(connection.user, 'is_active', None),
        "is_verified": getattr(connection.user, 'is_verified', None),
        "is_superuser": getattr(connection.user, 'is_superuser', None),
        "user_roles": [ur.role_name for ur in getattr(connection.user, 'roles', [])],
        "path": connection.url.path,
        "method": connection.method,
        "headers": dict(connection.headers),
        "client_host": connection.client.host if connection.client else None,
    }

def debug_guard_with_inspection(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """Guard that logs detailed request information."""
    inspection_data = inspect_request_for_guards(connection)
    logger.info("guard_debug", **inspection_data)

    # Original guard logic
    requires_active_user(connection, route_handler)
```

### Testing Guard Composition

```python
@pytest.mark.asyncio
async def test_guard_composition():
    """Test multiple guards working together."""
    user = m.User(is_active=False, is_verified=False, is_superuser=False)
    request = create_test_request(method="GET", path="/test")
    request._user = user

    # Test guard composition
    guards = [requires_active_user, requires_verified_user, requires_superuser]

    for i, guard in enumerate(guards):
        with pytest.raises(PermissionDeniedException):
            guard(request, None)

        # "Fix" the current issue and continue
        if i == 0:
            user.is_active = True
        elif i == 1:
            user.is_verified = True
        elif i == 2:
            user.is_superuser = True

    # All guards should pass now
    for guard in guards:
        guard(request, None)  # Should not raise
```

This comprehensive documentation covers all aspects of authorization guards and middleware in the Todo AI application, providing practical examples, performance optimization strategies, and testing approaches for secure access control implementation.