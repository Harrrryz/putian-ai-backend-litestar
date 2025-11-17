# User Management System Documentation

## Overview

The User Management System is a comprehensive component of the Todo AI application that handles user registration, authentication, authorization, and profile management. Built on top of the Litestar framework with SQLAlchemy ORM, it provides a secure and scalable foundation for managing user accounts with role-based access control (RBAC).

## Architecture

The user management system follows a layered architecture pattern:

- **Models Layer**: Database entities using SQLAlchemy ORM
- **Service Layer**: Business logic and data operations using Advanced Alchemy
- **Controller Layer**: HTTP API endpoints using Litestar
- **Schema Layer**: Pydantic models for request/response validation
- **Guard Layer**: Authentication and authorization middleware

## Database Models

### User Model (`User`)

The core user entity with comprehensive account management features.

**File**: `src/app/db/models/user.py`

```python
class User(UUIDAuditBase):
    __tablename__ = "user_account"
    __table_args__ = {"comment": "User accounts for application access"}
    __pii_columns__ = {"name", "email", "avatar_url"}
```

#### Core Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | UUID | Primary Key | Unique identifier |
| `email` | String | unique, indexed, required | User email address |
| `name` | String | nullable | Display name |
| `hashed_password` | String(255) | nullable | Hashed password |
| `avatar_url` | String(500) | nullable | Profile image URL |
| `is_active` | Boolean | default: True | Account status |
| `is_superuser` | Boolean | default: False | Superuser privilege |
| `is_verified` | Boolean | default: False | Email verification status |
| `verified_at` | Date | nullable | Email verification timestamp |
| `joined_at` | Date | default: now | Registration date |
| `login_count` | Integer | default: 0 | Login attempt counter |

#### Relationships

```python
# Role-based access control
roles: Mapped[list[UserRole]] = relationship(
    back_populates="user",
    lazy="selectin",
    uselist=True,
    cascade="all, delete",
)

# OAuth authentication
oauth_accounts: Mapped[list[UserOauthAccount]] = relationship(
    back_populates="user",
    lazy="noload",
    cascade="all, delete",
    uselist=True,
)

# User data (cascading delete)
todos: Mapped[list[Todo]] = relationship(back_populates="user", cascade="all, delete-orphan")
tags: Mapped[list[Tag]] = relationship(back_populates="user", cascade="all, delete-orphan")
agent_sessions: Mapped[list[AgentSession]] = relationship(back_populates="user", cascade="all, delete-orphan")

# System relationships
usage_quotas: Mapped[list[UserUsageQuota]] = relationship(back_populates="user")
verification_tokens: Mapped[list[EmailVerificationToken]] = relationship(back_populates="user")
password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(back_populates="user")
```

#### Hybrid Properties

```python
@hybrid_property
def has_password(self) -> bool:
    """Check if user has a password set."""
    return self.hashed_password is not None
```

### Role Model (`Role`)

Defines system roles for RBAC.

**File**: `src/app/db/models/role.py`

```python
class Role(UUIDAuditBase, SlugKey):
    __tablename__ = "role"

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
```

#### Default Roles

| Role Name | Description |
|-----------|-------------|
| `Application Access` | Default role for all users |
| `Superuser` | Administrative access |

### UserRole Model (`UserRole`)

Many-to-many relationship between users and roles.

**File**: `src/app/db/models/user_role.py`

```python
class UserRole(UUIDAuditBase):
    __tablename__ = "user_account_role"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    role_id: Mapped[UUID] = mapped_column(ForeignKey("role.id", ondelete="cascade"))
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
```

#### Association Proxies

```python
user_name: AssociationProxy[str] = association_proxy("user", "name")
user_email: AssociationProxy[str] = association_proxy("user", "email")
role_name: AssociationProxy[str] = association_proxy("role", "name")
role_slug: AssociationProxy[str] = association_proxy("role", "slug")
```

### OAuth Account Model (`UserOauthAccount`)

Stores OAuth provider authentication data.

**File**: `src/app/db/models/oauth_account.py`

```python
class UserOauthAccount(UUIDAuditBase):
    __tablename__ = "user_account_oauth"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    oauth_name: Mapped[str] = mapped_column(String(100), index=True)
    access_token: Mapped[str] = mapped_column(String(1024))
    account_id: Mapped[str] = mapped_column(String(320), index=True)
    account_email: Mapped[str] = mapped_column(String(320))
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
```

### Email Verification Token Model (`EmailVerificationToken`)

Handles email verification with expirable tokens.

**File**: `src/app/db/models/email_verification_token.py`

```python
class EmailVerificationToken(UUIDAuditBase):
    __tablename__ = "email_verification_token"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC) + timedelta(hours=24)
    )
    is_used: Mapped[bool] = mapped_column(default=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

#### Token Validation Properties

```python
@property
def is_expired(self) -> bool:
    """Check if the token has expired."""
    return datetime.now(UTC) > self.expires_at

@property
def is_valid(self) -> bool:
    """Check if the token is still valid (not used and not expired)."""
    return not self.is_used and not self.is_expired
```

## Service Layer

### UserService

**File**: `src/app/domain/accounts/services.py`

The main service class handling user operations and business logic.

#### Configuration

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    repository_type = UserRepository
    default_role = constants.DEFAULT_USER_ROLE  # "Application Access"
    match_fields = ["email"]
```

#### Key Methods

##### Authentication

```python
async def authenticate(self, username: str, password: bytes | str) -> m.User:
    """Authenticate a user against the stored hashed password."""
    db_obj = await self.get_one_or_none(email=username)
    if db_obj is None:
        raise PermissionDeniedException(detail="User not found or password invalid")
    if db_obj.hashed_password is None:
        raise PermissionDeniedException(detail="User not found or password invalid.")
    if not await crypt.verify_password(password, db_obj.hashed_password):
        raise PermissionDeniedException(detail="User not found or password invalid")
    if not db_obj.is_active:
        raise PermissionDeniedException(detail="User account is inactive")
    if not db_obj.is_verified:
        raise PermissionDeniedException(
            detail="User account is not verified. Please check your email for verification instructions."
        )
    return db_obj
```

##### Password Management

```python
async def update_password(self, data: dict[str, Any], db_obj: m.User) -> None:
    """Modify stored user password."""
    if not await crypt.verify_password(data["current_password"], db_obj.hashed_password):
        raise PermissionDeniedException(detail="User not found or password invalid.")
    if not db_obj.is_active:
        raise PermissionDeniedException(detail="User account is not active")
    if not db_obj.is_verified:
        raise PermissionDeniedException(detail="User account is not verified. Please verify your email first.")
    db_obj.hashed_password = await crypt.get_password_hash(data["new_password"])
    await self.repository.update(db_obj)
```

##### Role Checking

```python
@staticmethod
async def has_role_id(db_obj: m.User, role_id: UUID) -> bool:
    """Return true if user has specified role ID."""
    return any(assigned_role.role_id for assigned_role in db_obj.roles if assigned_role.role_id == role_id)

@staticmethod
async def has_role(db_obj: m.User, role_name: str) -> bool:
    """Return true if user has specified role name."""
    return any(assigned_role.role_name for assigned_role in db_obj.roles if assigned_role.role_name == role_name)

@staticmethod
def is_superuser(user: m.User) -> bool:
    """Check if user is a superuser."""
    return bool(
        user.is_superuser
        or any(assigned_role.role.name for assigned_role in user.roles if assigned_role.role.name in {"Superuser"})
    )
```

##### Email Verification

```python
async def verify_user_email(self, user_id: UUID) -> m.User:
    """Mark user as verified and update verification timestamp."""
    user = await self.get_one(id=user_id)

    # Update user verification status
    await self.update(
        item_id=user_id,
        data={
            "is_verified": True,
            "verified_at": datetime.now(UTC).date(),
        }
    )

    # Send welcome email (optional, don't fail if it fails)
    try:
        await self.send_welcome_email(user)
    except Exception:
        pass  # Log error but don't fail the verification process

    return await self.get_one(id=user_id)
```

##### Email Services

```python
async def send_verification_email(
    self,
    user: m.User,
    verification_token: str,
    base_url: str = "http://localhost:8081"
) -> bool:
    """Send verification email to user."""
    return await send_verification_email(
        smtp_settings=settings.smtp,
        to_email=user.email,
        user_name=user.name,
        verification_token=verification_token,
        base_url=base_url,
    )

async def send_welcome_email(self, user: m.User) -> bool:
    """Send welcome email to user after verification."""
    return await send_welcome_email(
        smtp_settings=settings.smtp,
        to_email=user.email,
        user_name=user.name,
    )
```

#### Model Population

```python
async def _populate_model(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
    """Populate model data with password hashing and role assignment."""
    data = schema_dump(data)
    data = await self._populate_with_hashed_password(data)
    return await self._populate_with_role(data)

async def _populate_with_hashed_password(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
    """Hash plain text passwords before database storage."""
    if is_dict(data) and (password := data.pop("password", None)) is not None:
        data["hashed_password"] = await crypt.get_password_hash(password)
    return data

async def _populate_with_role(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
    """Assign default role to new users."""
    if is_dict(data) and (role_id := data.pop("role_id", None)) is not None:
        data = await self.to_model(data)
        data.roles.append(m.UserRole(role_id=role_id, assigned_at=datetime.now(UTC)))
    return data
```

### RoleService

Handles role management operations.

```python
class RoleService(SQLAlchemyAsyncRepositoryService[m.Role]):
    repository_type = Repository
    match_fields = ["name"]

    async def to_model_on_create(self, data: ModelDictT[m.Role]) -> ModelDictT[m.Role]:
        """Generate slug from role name on creation."""
        data = schema_dump(data)
        if is_dict_without_field(data, "slug"):
            data["slug"] = await self.repository.get_available_slug(data["name"])
        return data
```

## API Controllers

### UserController

**File**: `src/app/domain/accounts/controllers/users.py`

Administrative user management endpoints. Requires superuser privileges.

#### Endpoints

| Method | Path | Description | Guards |
|--------|------|-------------|--------|
| GET | `/api/users` | List users with pagination and filtering | `requires_superuser` |
| GET | `/api/users/{user_id}` | Get specific user details | `requires_superuser` |
| POST | `/api/users` | Create new user | `requires_superuser` |
| PATCH | `/api/users/{user_id}` | Update user details | `requires_superuser` |
| DELETE | `/api/users/{user_id}` | Delete user | `requires_superuser` |

#### Implementation Examples

```python
@get(operation_id="ListUsers", path=urls.ACCOUNT_LIST, cache=60)
async def list_users(
    self,
    users_service: UserService,
    filters: Annotated[list[FilterTypes], Dependency(skip_validation=True)],
) -> OffsetPagination[User]:
    """List users with pagination and filtering."""
    results, total = await users_service.list_and_count(*filters)
    return users_service.to_schema(data=results, total=total, schema_type=User, filters=filters)

@post(operation_id="CreateUser", path=urls.ACCOUNT_CREATE)
async def create_user(self, users_service: UserService, data: UserCreate) -> User:
    """Create a new user."""
    db_obj = await users_service.create(data.to_dict())
    return users_service.to_schema(db_obj, schema_type=User)
```

#### Filtering Configuration

```python
dependencies = create_filter_dependencies({
    "id_filter": UUID,
    "search": "name,email",  # Search across name and email fields
    "pagination_type": "limit_offset",
    "pagination_size": 20,
    "created_at": True,
    "updated_at": True,
    "sort_field": "name",
    "sort_order": "asc",
})
```

### AccessController

**File**: `src/app/domain/accounts/controllers/access.py`

Handles user authentication, registration, and email verification.

#### Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/api/access/login` | User login | No |
| POST | `/api/access/logout` | User logout | No |
| POST | `/api/access/signup` | User registration | No |
| GET | `/api/access/verify-email` | Email verification (GET) | No |
| POST | `/api/access/verify-email` | Email verification (POST) | No |
| POST | `/api/access/resend-verification` | Resend verification email | No |
| GET | `/api/me` | Get current user profile | Yes |

#### Registration Flow

```python
@post(operation_id="AccountRegister", path=urls.ACCOUNT_REGISTER)
async def signup(
    self,
    request: Request,
    users_service: UserService,
    roles_service: RoleService,
    email_verification_service: EmailVerificationService,
    data: AccountRegister,
) -> User:
    """User Signup with email verification."""
    user_data = data.to_dict()

    # Set user as unverified by default
    user_data["is_verified"] = False

    # Add default role
    role_obj = await roles_service.get_one_or_none(slug=slugify(users_service.default_role))
    if role_obj is not None:
        user_data.update({"role_id": role_obj.id})

    # Create user
    user = await users_service.create(user_data)

    # Create verification token
    verification_token = await email_verification_service.create_verification_token(user.id)

    # Send verification email
    base_url = f"{request.base_url.scheme}://{request.base_url.netloc}"
    email_sent = await users_service.send_verification_email(
        user=user,
        verification_token=verification_token.token,
        base_url=base_url
    )

    # Emit user creation event
    request.app.emit(event_id="user_created", user_id=user.id, email_sent=email_sent)

    return users_service.to_schema(user, schema_type=User)
```

#### Email Verification

```python
@get(operation_id="VerifyEmailGet", path=urls.ACCOUNT_VERIFY_EMAIL, exclude_from_auth=True)
async def verify_email_get(
    self,
    users_service: UserService,
    email_verification_service: EmailVerificationService,
    token: str = Parameter(query="token"),
) -> Response:
    """Verify user email with verification token via GET request."""
    try:
        # Verify the token and get the user
        user = await email_verification_service.verify_token(token)

        # Mark user as verified
        await users_service.verify_user_email(user.id)

        # Return success HTML page
        success_html = f"""<!DOCTYPE html>..."""  # HTML template
        return Response(content=success_html, status_code=200, media_type="text/html")

    except Exception as e:
        # Return error HTML page
        error_html = f"""<!DOCTYPE html>..."""  # Error template
        return Response(content=error_html, status_code=400, media_type="text/html")
```

## Schemas and DTOs

**File**: `src/app/domain/accounts/schemas.py`

### Base Model

```python
class PydanticBaseModel(BaseModel):
    """Base model with camel case config."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda s: "".join(
            [s[0].lower(), *[c if c.islower() else f"_{c.lower()}" for c in s[1:]]]
        ).replace("_", ""),
    )
```

### User Schemas

#### User Response Schema

```python
class User(PydanticBaseModel):
    """User properties to use for a response."""

    id: UUID
    email: str
    name: str | None = None
    is_superuser: bool = False
    is_active: bool = False
    is_verified: bool = False
    has_password: bool = False
    roles: list[UserRole] = Field(default_factory=list)
    oauth_accounts: list[OauthAccount] = Field(default_factory=list)
```

#### User Creation Schema

```python
class UserCreate(PydanticBaseModel):
    """Schema for user creation."""

    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None
    is_superuser: bool = False
    is_active: bool = True
    is_verified: bool = False
```

#### User Update Schema

```python
class UserUpdate(PydanticBaseModel):
    """Schema for user updates."""

    email: EmailStr | None = None
    password: str | None = None
    name: str | None = None
    is_superuser: bool | None = None
    is_active: bool | None = None
    is_verified: bool | None = None

    model_config = ConfigDict(extra="ignore")
```

### Authentication Schemas

```python
class AccountLogin(PydanticBaseModel):
    """Login credentials schema."""

    username: str = Field(min_length=3)
    password: str = Field(min_length=6)

class AccountRegister(PydanticBaseModel):
    """Registration schema."""

    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None
```

## Security and Authentication

### Password Security

**File**: `src/app/lib/crypt.py`

Uses Argon2 password hashing for secure password storage.

```python
from passlib.context import CryptContext

password_crypt_context = CryptContext(schemes=["argon2"], deprecated="auto")

async def get_password_hash(password: str | bytes) -> str:
    """Hash a password using Argon2."""
    return await asyncio.get_running_loop().run_in_executor(
        None, password_crypt_context.hash, password
    )

async def verify_password(plain_password: str | bytes, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    valid, _ = await asyncio.get_running_loop().run_in_executor(
        None, password_crypt_context.verify_and_update, plain_password, hashed_password
    )
    return bool(valid)
```

### JWT Authentication

**File**: `src/app/domain/accounts/guards.py`

#### Authentication Guard

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

#### User Retrieval

```python
async def current_user_from_token(token: Token, connection: ASGIConnection) -> m.User | None:
    """Lookup current user from local JWT token."""
    service = await anext(provide_users_service(alchemy.provide_session(connection.app.state, connection.scope)))
    user = await service.get_one_or_none(email=token.sub)
    return user if user and user.is_active and user.is_verified else None
```

### Authorization Guards

```python
def requires_active_user(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Request requires active user."""
    if connection.user.is_active:
        return
    raise PermissionDeniedException("Inactive account")

def requires_superuser(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Request requires active superuser."""
    if connection.user.is_superuser:
        return
    raise PermissionDeniedException(detail="Insufficient privileges")

def requires_verified_user(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Require verified user."""
    if connection.user.is_verified:
        return
    raise PermissionDeniedException(detail="User account is not verified.")
```

## Dependency Injection

**File**: `src/app/domain/accounts/deps.py`

### Service Provider

```python
provide_users_service = create_service_provider(
    UserService,
    load=[
        selectinload(m.User.roles).options(joinedload(m.UserRole.role, innerjoin=True)),
        selectinload(m.User.oauth_accounts),
    ],
    error_messages={
        "duplicate_key": "This user already exists.",
        "integrity": "User operation failed.",
    },
)
```

### Current User Provider

```python
async def provide_user(request: Request[m.User, Any, Any]) -> m.User:
    """Get the user from the request."""
    return request.user
```

## URL Configuration

**File**: `src/app/domain/accounts/urls.py`

```python
# Authentication and Access
ACCOUNT_LOGIN = "/api/access/login"
ACCOUNT_LOGOUT = "/api/access/logout"
ACCOUNT_REGISTER = "/api/access/signup"
ACCOUNT_VERIFY_EMAIL = "/api/access/verify-email"
ACCOUNT_RESEND_VERIFICATION = "/api/access/resend-verification"
ACCOUNT_PROFILE = "/api/me"

# User Management (Admin)
ACCOUNT_LIST = "/api/users"
ACCOUNT_CREATE = "/api/users"
ACCOUNT_DETAIL = "/api/users/{user_id:uuid}"
ACCOUNT_UPDATE = "/api/users/{user_id:uuid}"
ACCOUNT_DELETE = "/api/users/{user_id:uuid}"

# Role Management
ACCOUNT_ASSIGN_ROLE = "/api/roles/{role_slug:str}/assign"
ACCOUNT_REVOKE_ROLE = "/api/roles/{role_slug:str}/revoke"
```

## Business Rules and Validation

### User Registration Rules

1. **Email Validation**: Must be a valid email format and unique
2. **Password Requirements**: Minimum 6 characters
3. **Default Role**: Automatically assigned "Application Access" role
4. **Email Verification**: Users start unverified and must verify email
5. **Account Status**: New accounts are active but unverified

### Authentication Rules

1. **Active Users Only**: Inactive users cannot authenticate
2. **Verified Users Only**: Unverified users cannot authenticate
3. **Password Verification**: Argon2 hash verification
4. **Login Attempts**: Tracked via login_count field

### Authorization Rules

1. **Superuser Required**: Administrative endpoints require superuser status
2. **Role-Based Access**: Role checking methods available
3. **Resource Ownership**: Users can only access their own resources
4. **Active User Guard**: Most endpoints require active user status

### Email Verification Rules

1. **Token Expiration**: 24-hour token validity
2. **Single Use**: Tokens are marked as used after verification
3. **Resend Limit**: New token created only if none exists
4. **Welcome Email**: Sent after successful verification

## Error Handling

### Common Exceptions

| Exception | Cause | HTTP Status |
|-----------|-------|-------------|
| `PermissionDeniedException` | Authentication/authorization failure | 401/403 |
| `RepositoryError` | Database constraint violations | 400/409 |
| `ValidationError` | Schema validation failure | 400 |
| `NotFoundError` | Resource not found | 404 |

### Validation Error Examples

```python
# Email already exists
{
    "detail": "This user already exists.",
    "status_code": 400
}

# Invalid credentials
{
    "detail": "User not found or password invalid",
    "status_code": 401
}

# Inactive account
{
    "detail": "User account is inactive",
    "status_code": 401
}

# Unverified account
{
    "detail": "User account is not verified. Please check your email for verification instructions.",
    "status_code": 401
}
```

## Database Relationships and Constraints

### Foreign Key Constraints

```sql
-- User relationships with cascade delete
FOREIGN KEY (user_id) REFERENCES user_account(id) ON DELETE CASCADE

-- Role relationships with cascade delete
FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
```

### Unique Constraints

```sql
-- User email uniqueness
UNIQUE (email)

-- Role name uniqueness
UNIQUE (name)

-- Verification token uniqueness
UNIQUE (token)
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_user_account_email ON user_account(email);
CREATE INDEX idx_user_account_oauth_oauth_name ON user_account_oauth(oauth_name);
CREATE INDEX idx_user_account_oauth_account_id ON user_account_oauth(account_id);
CREATE INDEX idx_email_verification_token_token ON email_verification_token(token);
CREATE INDEX idx_email_verification_token_user_id ON email_verification_token(user_id);
```

## Configuration and Constants

**File**: `src/app/config/constants.py`

```python
DEFAULT_USER_ROLE = "Application Access"  # Default role for new users
SUPERUSER_ACCESS_ROLE = "Superuser"       # Administrative role
DEFAULT_PAGINATION_SIZE = 20              # Default page size for user lists
```

## Usage Examples

### Creating a User (Admin)

```bash
curl -X POST "http://localhost:8000/api/users" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "name": "John Doe",
    "is_active": true
  }'
```

### User Login

```bash
curl -X POST "http://localhost:8000/api/access/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword123"
```

### User Registration

```bash
curl -X POST "http://localhost:8000/api/access/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "password123",
    "name": "Jane Smith"
  }'
```

### Get User Profile

```bash
curl -X GET "http://localhost:8000/api/me" \
  -H "Authorization: Bearer <user-token>"
```

### List Users (Admin)

```bash
curl -X GET "http://localhost:8000/api/users?page=1&limit=10&search=john" \
  -H "Authorization: Bearer <admin-token>"
```

## Security Considerations

1. **Password Security**: Uses Argon2 for password hashing
2. **PII Protection**: PII columns marked in models for data protection
3. **Token Security**: JWT tokens with proper expiration
4. **SQL Injection Prevention**: SQLAlchemy ORM usage
5. **Rate Limiting**: Consider implementing for authentication endpoints
6. **Email Security**: Verification tokens with expiration and single use

## Testing Considerations

1. **Unit Tests**: Test service layer business logic
2. **Integration Tests**: Test API endpoints with database
3. **Authentication Tests**: Verify JWT flow and guards
4. **Authorization Tests**: Verify role-based access control
5. **Email Tests**: Mock email services for verification flow

## Migration Notes

When upgrading the user management system:

1. **Database Migrations**: Use Alembic for schema changes
2. **Password Migration**: Consider re-hashing passwords with new algorithms
3. **Backward Compatibility**: Maintain API compatibility where possible
4. **Data Validation**: Validate existing data against new constraints
5. **Email Verification**: Handle unverified users from previous versions

This documentation provides a comprehensive overview of the User Management System. For specific implementation details, refer to the source code files mentioned throughout this document.