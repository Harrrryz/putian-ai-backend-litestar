# Authentication & Authorization Guide

This guide provides comprehensive documentation for the authentication and authorization system in the Todo AI application. The system is built on Litestar with JWT-based authentication, OAuth2 integration, and role-based access control (RBAC).

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [JWT Authentication Implementation](#jwt-authentication-implementation)
3. [OAuth2 Integration (GitHub)](#oauth2-integration-github)
4. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
5. [Authentication Guards and Middleware](#authentication-guards-and-middleware)
6. [Password Hashing and Security](#password-hashing-and-security)
7. [Token Management and Refresh](#token-management-and-refresh)
8. [Session Security Best Practices](#session-security-best-practices)
9. [API Endpoint Protection Patterns](#api-endpoint-protection-patterns)
10. [Configuration and Setup](#configuration-and-setup)
11. [Security Considerations](#security-considerations)

## Architecture Overview

The authentication system follows a layered architecture:

- **Models Layer**: Database models for users, roles, and OAuth accounts
- **Services Layer**: Business logic for authentication, user management, and authorization
- **Guards Layer**: Authorization decorators and middleware
- **Controllers Layer**: HTTP endpoints handling authentication flows
- **Configuration Layer**: Settings and environment-based configuration

### Key Components

- **JWT Authentication**: Token-based authentication using Litestar's built-in JWT support
- **OAuth2**: Social login integration with GitHub
- **RBAC**: Role-based access control with fine-grained permissions
- **Email Verification**: Mandatory email verification for new users
- **Password Security**: Argon2 hashing with salted passwords

## JWT Authentication Implementation

### Core Configuration

The JWT authentication is configured in `src/app/domain/accounts/guards.py`:

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

The `current_user_from_token` function validates JWT tokens and retrieves user data:

```python
async def current_user_from_token(token: Token, connection: ASGIConnection[Any, Any, Any, Any]) -> m.User | None:
    """Lookup current user from local JWT token."""
    service = await anext(provide_users_service(alchemy.provide_session(connection.app.state, connection.scope)))
    user = await service.get_one_or_none(email=token.sub)
    return user if user and user.is_active and user.is_verified else None
```

### Token Payload Structure

JWT tokens contain the following claims:
- `sub`: User email (subject identifier)
- Standard JWT claims (exp, iat, etc.)

### Authentication Flow

1. User submits credentials to `/api/access/login`
2. Service validates credentials against hashed password
3. JWT token is generated with user email as subject
4. Token is returned in response and stored in HTTP-only cookie
5. Subsequent requests include token in Authorization header or cookie
6. Middleware validates token and injects user into request context

## OAuth2 Integration (GitHub)

### Configuration

GitHub OAuth2 is configured in `src/app/config/app.py`:

```python
github_oauth = GitHubOAuth2(
    client_id=settings.app.GITHUB_OAUTH2_CLIENT_ID,
    client_secret=settings.app.GITHUB_OAUTH2_CLIENT_SECRET,
)
```

### Environment Variables

Required environment variables:

```bash
GITHUB_OAUTH2_CLIENT_ID=your_github_client_id
GITHUB_OAUTH2_CLIENT_SECRET=your_github_client_secret
```

### OAuth2 Flow

1. User initiates OAuth login via frontend
2. Redirect to GitHub authorization page
3. User authorizes application
4. GitHub redirects to callback with authorization code
5. Exchange code for access token
6. Retrieve user profile from GitHub API
7. Create or update user account with OAuth data
8. Generate JWT token and authenticate user

### OAuth2 Account Model

```python
class UserOauthAccount(UUIDAuditBase):
    """User Oauth Account"""

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    oauth_name: Mapped[str] = mapped_column(String(length=100), index=True)
    access_token: Mapped[str] = mapped_column(String(length=1024))
    expires_at: Mapped[int | None] = mapped_column(Integer)
    refresh_token: Mapped[str | None] = mapped_column(String(length=1024))
    account_id: Mapped[str] = mapped_column(String(length=320), index=True)
    account_email: Mapped[str] = mapped_column(String(length=320))
```

## Role-Based Access Control (RBAC)

### Data Model

The RBAC system uses three core models:

#### User Model
```python
class User(UUIDAuditBase):
    email: Mapped[str] = mapped_column(unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    roles: Mapped[list[UserRole]] = relationship(back_populates="user")
```

#### Role Model
```python
class Role(UUIDAuditBase, SlugKey):
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    users: Mapped[list[UserRole]] = relationship(back_populates="role")
```

#### UserRole (Join Table)
```python
class UserRole(UUIDAuditBase):
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="cascade"))
    role_id: Mapped[UUID] = mapped_column(ForeignKey("role.id", ondelete="cascade"))
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
```

### Default Roles

- **Application Access**: Default role for all verified users
- **Superuser**: Administrative access with full permissions

### Role Checking Service

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    @staticmethod
    async def has_role_id(db_obj: m.User, role_id: UUID) -> bool:
        """Return true if user has specified role ID"""
        return any(assigned_role.role_id for assigned_role in db_obj.roles if assigned_role.role_id == role_id)

    @staticmethod
    async def has_role(db_obj: m.User, role_name: str) -> bool:
        """Return true if user has specified role"""
        return any(assigned_role.role_name for assigned_role in db_obj.roles if assigned_role.role_name == role_name)

    @staticmethod
    def is_superuser(user: m.User) -> bool:
        return bool(
            user.is_superuser
            or any(assigned_role.role.name for assigned_role in user.roles if assigned_role.role.name in {"Superuser"}),
        )
```

## Authentication Guards and Middleware

### Available Guards

#### `requires_active_user`
Ensures the user account is active:

```python
def requires_active_user(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    if connection.user.is_active:
        return
    raise PermissionDeniedException("Inactive account")
```

#### `requires_superuser`
Ensures the user has superuser privileges:

```python
def requires_superuser(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    if connection.user.is_superuser:
        return
    raise PermissionDeniedException(detail="Insufficient privileges")
```

#### `requires_verified_user`
Ensures the user's email is verified:

```python
def requires_verified_user(connection: ASGIConnection[m.User, Any, Any, Any], _: BaseRouteHandler) -> None:
    if connection.user.is_verified:
        return
    raise PermissionDeniedException(detail="User account is not verified.")
```

### Usage Examples

```python
# Controller-level guard
class UserController(Controller):
    guards = [requires_superuser]

    @get("/users/{user_id}")
    async def get_user(self, user_id: UUID) -> User:
        # Only superusers can access this endpoint
        pass

# Route-level guard
@get("/profile", guards=[requires_active_user])
async def get_profile(self, current_user: User) -> User:
    # Only active users can access their profile
    pass
```

### Middleware Configuration

JWT authentication middleware is automatically configured through the `auth` instance in `src/app/domain/accounts/guards.py`. It:

- Extracts tokens from Authorization header or cookies
- Validates token signature and expiration
- Retrieves and injects user into request context
- Handles authentication errors

## Password Hashing and Security

### Hashing Algorithm

The application uses **Argon2** for password hashing, configured in `src/app/lib/crypt.py`:

```python
password_crypt_context = CryptContext(schemes=["argon2"], deprecated="auto")
```

### Hashing Functions

```python
async def get_password_hash(password: str | bytes) -> str:
    """Generate password hash using Argon2"""
    return await asyncio.get_running_loop().run_in_executor(None, password_crypt_context.hash, password)

async def verify_password(plain_password: str | bytes, hashed_password: str) -> bool:
    """Verify password against hash"""
    valid, _ = await asyncio.get_running_loop().run_in_executor(
        None,
        password_crypt_context.verify_and_update,
        plain_password,
        hashed_password,
    )
    return bool(valid)
```

### Password Policies

- **Minimum Length**: No explicit minimum, but validation occurs at service level
- **Complexity**: No explicit requirements, but can be added via Pydantic validators
- **Hashing**: Argon2 with automatic salt generation
- **Deprecated Schemes**: Automatic migration from deprecated hashing schemes

### Authentication Service

```python
async def authenticate(self, username: str, password: bytes | str) -> m.User:
    """Authenticate a user against the stored hashed password."""
    db_obj = await self.get_one_or_none(email=username)
    if db_obj is None:
        raise PermissionDeniedException(detail="User not found or password invalid")
    if not await crypt.verify_password(password, db_obj.hashed_password):
        raise PermissionDeniedException(detail="User not found or password invalid")
    if not db_obj.is_active:
        raise PermissionDeniedException(detail="User account is inactive")
    if not db_obj.is_verified:
        raise PermissionDeniedException(detail="User account is not verified")
    return db_obj
```

## Token Management and Refresh

### JWT Token Configuration

Tokens are configured with the following settings:

```python
JWT_ENCRYPTION_ALGORITHM: str = "HS256"  # HMAC-SHA256
SECRET_KEY: str  # Application secret key (environment variable)
```

### Token Storage

JWT tokens are stored in:
1. **HTTP-only Cookies**: Primary storage method
2. **Authorization Header**: Fallback for API clients

### Token Expiration

- **Default**: 15 minutes (configurable via Litestar JWT settings)
- **Refresh**: Currently not implemented - requires re-authentication

### Logout Implementation

```python
@post("/api/access/logout", exclude_from_auth=True)
async def logout(self, request: Request) -> Response:
    """Account Logout"""
    request.cookies.pop(auth.key, None)
    request.clear_session()

    response = Response({"message": "OK"}, status_code=200)
    response.delete_cookie(auth.key)

    return response
```

## Session Security Best Practices

### Security Headers

The application implements several security headers:

```python
CSRF_COOKIE_NAME: str = "XSRF-TOKEN"
CSRF_COOKIE_SECURE: bool = False  # Set to True in production
```

### Cookie Configuration

- **HTTP-only**: JWT cookies are HTTP-only to prevent XSS attacks
- **Secure**: Set to `True` in production for HTTPS-only
- **SameSite**: Configured via Litestar's CSRF middleware

### Email Verification

All new users must verify their email addresses:

1. User registration creates unverified account
2. Verification email with token is sent
3. User clicks verification link or submits token
4. Account is marked as verified
5. Welcome email is sent

### Password Reset

The application includes password reset functionality:

1. User requests reset via email
2. Secure token is generated and emailed
3. User submits token with new password
4. Password is updated and token is invalidated

## API Endpoint Protection Patterns

### Authentication Exclusions

Certain endpoints are excluded from authentication:

```python
exclude=[
    constants.HEALTH_ENDPOINT,           # /health
    urls.ACCOUNT_LOGIN,                  # /api/access/login
    urls.ACCOUNT_REGISTER,               # /api/access/signup
    urls.ACCOUNT_VERIFY_EMAIL,           # /api/access/verify-email
    urls.ACCOUNT_RESEND_VERIFICATION,    # /api/access/resend-verification
    "^/schema",                          # OpenAPI schema
    "^/public/",                         # Public assets
]
```

### Protection Levels

#### Level 1: Public Access
```python
@get("/health", exclude_from_auth=True)
async def health_check() -> dict:
    return {"status": "healthy"}
```

#### Level 2: Authentication Required
```python
@get("/profile", guards=[requires_active_user])
async def get_profile(self, current_user: User) -> User:
    return current_user
```

#### Level 3: Email Verification Required
```python
@get("/protected-feature", guards=[requires_verified_user])
async def protected_feature(self, current_user: User) -> dict:
    return {"message": "Access granted"}
```

#### Level 4: Superuser Only
```python
@delete("/admin/users/{user_id}", guards=[requires_superuser])
async def delete_user(self, user_id: UUID) -> None:
    # Admin-only functionality
    pass
```

### Controller-Level Protection

```python
class UserController(Controller):
    tags = ["User Accounts"]
    guards = [requires_superuser]  # All endpoints require superuser
    dependencies = {
        "users_service": Provide(provide_users_service),
    }
```

## Configuration and Setup

### Environment Variables

Required for authentication:

```bash
# Core Security
SECRET_KEY=your_very_long_secret_key_here
JWT_ENCRYPTION_ALGORITHM=HS256

# OAuth2 (GitHub)
GITHUB_OAUTH2_CLIENT_ID=your_github_client_id
GITHUB_OAUTH2_CLIENT_SECRET=your_github_client_secret

# Email Configuration (for verification)
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USERNAME=your_email@domain.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true
```

### Application Configuration

Authentication is configured in `src/app/server/core.py`:

```python
# JWT auth configuration
app_config = jwt_auth.on_app_init(app_config)

# Dependencies for user injection
dependencies = {"current_user": Provide(provide_user)}
app_config.dependencies.update(dependencies)

# OpenAPI integration
app_config.openapi_config = OpenAPIConfig(
    title=settings.app.NAME,
    version=current_version,
    components=[jwt_auth.openapi_components],
    security=[jwt_auth.security_requirement],
    use_handler_docstrings=True,
    render_plugins=[ScalarRenderPlugin(version="latest")],
)
```

### Database Setup

Run migrations to create authentication tables:

```bash
# Create migration
uv run app database make-migrations --message "Add authentication tables"

# Apply migrations
uv run app database upgrade
```

### Default User Creation

Create initial admin user:

```bash
# Create user
uv run app user create --email admin@example.com --password secure_password

# Promote to superuser
uv run app user promote --email admin@example.com
```

## Security Considerations

### Password Security

- **Hashing**: Argon2 with salted hashes
- **Storage**: Hashes only, never plain text passwords
- **Validation**: Password strength validation recommended
- **Reset**: Secure token-based password reset

### Token Security

- **Algorithm**: HMAC-SHA256 for JWT signing
- **Secret**: Strong, randomly generated secret key
- **Expiration**: Short token lifetime (15 minutes)
- **Storage**: HTTP-only cookies prevent XSS attacks

### Session Security

- **HTTPS**: Required in production (secure cookies)
- **CSRF**: Cross-site request forgery protection
- **XSS**: Content Security Headers recommended
- **Rate Limiting**: Implement for authentication endpoints

### Email Security

- **Verification**: Mandatory email verification
- **Tokens**: Secure, expiring verification tokens
- **Transport**: TLS for SMTP connections
- **Templates**: HTML sanitization in email templates

### OAuth2 Security

- **State**: CSRF protection with state parameter
- **Scopes**: Minimal OAuth scopes requested
- **Storage**: Encrypted OAuth tokens in database
- **Revocation**: OAuth token revocation capability

### Data Protection

- **PII**: Personal data marked and protected
- **Audit**: User activity logging
- **Deletion**: GDPR-compliant data deletion
- **Retention**: Configurable data retention policies

## Development and Testing

### Authentication Testing

```python
# Test user creation
async def test_user_registration():
    user_data = {
        "email": "test@example.com",
        "password": "secure_password",
        "name": "Test User"
    }
    response = await client.post("/api/access/signup", json=user_data)
    assert response.status_code == 201

# Test authentication
async def test_user_login():
    login_data = {"username": "test@example.com", "password": "secure_password"}
    response = await client.post("/api/access/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Security Testing

- **OWASP Top 10**: Regular security audits
- **Penetration Testing**: External security assessments
- **Dependency Scanning**: Automated vulnerability scanning
- **Code Review**: Security-focused code reviews

### Monitoring and Logging

- **Failed Logins**: Monitor for brute force attacks
- **Token Usage**: Track unusual token usage patterns
- **Account Changes**: Log all account modifications
- **Security Events**: Real-time security event monitoring

This comprehensive authentication and authorization system provides a secure foundation for the Todo AI application while maintaining flexibility for future enhancements and compliance with security best practices.