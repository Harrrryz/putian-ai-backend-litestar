# JWT Authentication Implementation

This document provides comprehensive documentation for the JWT (JSON Web Token) authentication system in the Todo AI application. The implementation uses Litestar's built-in JWT support with OAuth2 Password Bearer authentication.

## Table of Contents

1. [JWT Token Architecture and Design](#jwt-token-architecture-and-design)
2. [Token Generation and Signing Processes](#token-generation-and-signing-processes)
3. [Token Validation and Verification Flows](#token-validation-and-verification-flows)
4. [JWT Middleware and Guard Implementation](#jwt-middleware-and-guard-implementation)
5. [Token Refresh and Expiration Handling](#token-refresh-and-expiration-handling)
6. [User Session Management with JWT](#user-session-management-with-jwt)
7. [Security Best Practices for JWT](#security-best-practices-for-jwt)
8. [JWT Configuration and Settings](#jwt-configuration-and-settings)
9. [Token Storage and Transmission](#token-storage-and-transmission)
10. [JWT Troubleshooting and Debugging](#jwt-troubleshooting-and-debugging)

## JWT Token Architecture and Design

### Overview

The JWT authentication system in this application follows the OAuth2 Password Bearer flow with the following architecture:

- **Framework**: Litestar with built-in JWT support
- **Algorithm**: HMAC-SHA256 (HS256) for token signing
- **Token Format**: Standard JWT with custom claims
- **Authentication Flow**: OAuth2 Password Bearer with email/password credentials

### Token Structure

```python
# JWT Token Claims
{
    "sub": "user@example.com",      # Subject (user email)
    "exp": 1640995200,              # Expiration timestamp
    "iat": 1640991600,              # Issued at timestamp
    "type": "access"                # Token type (implicit from Litestar)
}
```

### Authentication Architecture Components

1. **OAuth2PasswordBearerAuth**: Main authentication handler
2. **Token Retrieval Handler**: Validates tokens and retrieves users
3. **Guards**: Authorization decorators for route protection
4. **Middleware**: Automatic token processing for protected routes

## Token Generation and Signing Processes

### Login Endpoint

The token generation process is handled by the login endpoint in `src/app/domain/accounts/controllers/access.py`:

```python
@post(operation_id="AccountLogin", path=urls.ACCOUNT_LOGIN, exclude_from_auth=True)
async def login(
    self,
    users_service: UserService,
    data: Annotated[AccountLogin, Body(title="OAuth2 Login", media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[OAuth2Login]:
    """Authenticate a user."""
    user = await users_service.authenticate(data.username, data.password)
    return auth.login(user.email)
```

### Authentication Process

1. **User Authentication**: Validate credentials against the database
2. **Token Creation**: Generate JWT token with user email as subject
3. **Token Signing**: Sign token using application secret key and HS256 algorithm
4. **Response**: Return OAuth2Login response with access token

### Token Creation

The actual token creation is handled by Litestar's `OAuth2PasswordBearerAuth`:

```python
# Token creation (internal Litestar implementation)
def create_token(self, identifier: str) -> str:
    """Create a JWT token for the given identifier."""
    token_data = {
        "sub": identifier,  # User email
        "exp": datetime.utcnow() + timedelta(minutes=15),  # Default expiration
        "iat": datetime.utcnow(),
    }
    return jwt.encode(token_data, self.token_secret, algorithm=self.algorithm)
```

## Token Validation and Verification Flows

### Token Retrieval Handler

The core token validation logic is implemented in `src/app/domain/accounts/guards.py`:

```python
async def current_user_from_token(token: Token, connection: ASGIConnection[Any, Any, Any, Any]) -> m.User | None:
    """Lookup current user from local JWT token.

    Fetches the user information from the database and validates:
    - User exists
    - User is active
    - User is verified

    Returns:
        User: User record mapped to the JWT identifier if user exists, is active, and is verified
    """
    service = await anext(provide_users_service(alchemy.provide_session(connection.app.state, connection.scope)))
    user = await service.get_one_or_none(email=token.sub)
    return user if user and user.is_active and user.is_verified else None
```

### Validation Flow

1. **Token Extraction**: Extract JWT from Authorization header
2. **Token Verification**: Verify signature using application secret key
3. **Claim Validation**: Validate standard JWT claims (exp, iat, etc.)
4. **User Lookup**: Retrieve user from database using email subject
5. **User Status Check**: Verify user is active and verified
6. **User Injection**: Inject user object into request context

### Token Structure

```python
# Token object structure (from Litestar)
class Token:
    sub: str      # Subject (user email)
    exp: int      # Expiration timestamp
    iat: int      # Issued at timestamp
    # Additional claims can be added as needed
```

## JWT Middleware and Guard Implementation

### Authentication Configuration

The main authentication configuration is in `src/app/domain/accounts/guards.py`:

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

### Application Integration

The authentication middleware is configured in `src/app/server/core.py`:

```python
# JWT auth configuration
app_config = jwt_auth.on_app_init(app_config)

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

### Guard Functions

Several guard functions are implemented for different authorization levels:

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
    """Verify the connection user is a verified user."""
    if connection.user.is_verified:
        return
    raise PermissionDeniedException(detail="User account is not verified.")
```

### Route Protection

Routes are protected using the `guards` parameter:

```python
@get(operation_id="AccountProfile", path=urls.ACCOUNT_PROFILE, guards=[requires_active_user])
async def profile(self, current_user: m.User, users_service: UserService) -> User:
    """User Profile."""
    return users_service.to_schema(current_user, schema_type=User)
```

## Token Refresh and Expiration Handling

### Default Token Configuration

The JWT token expiration is managed by Litestar's default settings:

- **Default Expiration**: 15 minutes
- **Algorithm**: HS256 (HMAC-SHA256)
- **Token Type**: Access token (no refresh token implementation currently)

### Token Expiration

Tokens automatically expire after the configured duration. When a token expires:

1. **Client Detection**: Client receives 401 Unauthorized response
2. **Re-authentication**: User must log in again with credentials
3. **New Token**: System generates new JWT token

### Current Limitations

- No automatic token refresh mechanism
- No refresh token implementation
- Fixed 15-minute expiration (not configurable without code changes)

### Future Enhancements

For production use, consider implementing:

```python
# Example refresh token implementation
@post("/auth/refresh")
async def refresh_token(refresh_token: str) -> OAuth2Login:
    """Refresh access token using refresh token."""
    # Validate refresh token
    # Generate new access token
    # Return new token
    pass
```

## User Session Management with JWT

### Stateless Sessions

JWT authentication provides stateless session management:

- **No Server Storage**: No session data stored on server
- **Client Storage**: Tokens stored on client (memory/localStorage/cookies)
- **Database Validation**: User status validated on each request
- **Scalable**: Suitable for distributed systems

### User Context

User context is automatically injected into requests:

```python
async def provide_user(request: Request[m.User, Any, Any]) -> m.User:
    """Get the user from the request."""
    return request.user
```

### Session Lifecycle

1. **Login**: User authenticates with email/password
2. **Token Generation**: JWT token created and returned
3. **Token Storage**: Client stores token (typically Authorization header)
4. **Token Usage**: Client includes token in subsequent requests
5. **Token Validation**: Server validates token on each request
6. **Logout**: Client discards token (server-side invalidation not implemented)

### Logout Implementation

```python
@post(operation_id="AccountLogout", path=urls.ACCOUNT_LOGOUT, exclude_from_auth=True)
async def logout(self, request: Request) -> Response:
    """Account Logout"""
    request.cookies.pop(auth.key, None)
    request.clear_session()

    response = Response({"message": "OK"}, status_code=200)
    response.delete_cookie(auth.key)
    return response
```

## Security Best Practices for JWT

### Implementation Security

1. **Strong Secret Keys**: Use cryptographically strong secret keys
2. **Algorithm Specification**: Explicitly specify HS256 algorithm
3. **Token Expiration**: Set reasonable token expiration times
4. **HTTPS Only**: Always use HTTPS in production
5. **Input Validation**: Validate all authentication inputs

### Secret Key Management

```python
# Configuration in src/app/config/base.py
SECRET_KEY: str = field(
    default_factory=get_env("SECRET_KEY", binascii.hexlify(
        os.urandom(32)).decode(encoding="utf-8")),
)
```

### Security Headers

```python
# CSRF protection configuration
csrf = CSRFConfig(
    secret=settings.app.SECRET_KEY,
    cookie_secure=settings.app.CSRF_COOKIE_SECURE,
    cookie_name=settings.app.CSRF_COOKIE_NAME,
)
```

### Token Security Considerations

- **No Sensitive Data**: Never store sensitive information in JWT payload
- **Short Expiration**: Use short token lifetimes (15 minutes recommended)
- **Token Revocation**: Implement token blacklisting if needed
- **Rate Limiting**: Implement rate limiting on authentication endpoints
- **Audit Logging**: Log authentication attempts for security monitoring

### Input Validation

```python
class AccountLogin(PydanticBaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)

class AccountRegister(PydanticBaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None
```

## JWT Configuration and Settings

### Environment Variables

```python
# JWT Configuration
SECRET_KEY                    # JWT signing key (required)
JWT_ENCRYPTION_ALGORITHM      # JWT algorithm (default: "HS256")

# Security Configuration
CSRF_COOKIE_NAME             # CSRF cookie name (default: "XSRF-TOKEN")
CSRF_COOKIE_SECURE           # CSRF cookie secure flag (default: False)
```

### Application Settings

```python
@dataclass
class AppSettings:
    """Application configuration"""

    SECRET_KEY: str = field(
        default_factory=get_env("SECRET_KEY", binascii.hexlify(
            os.urandom(32)).decode(encoding="utf-8")),
    )
    """Application secret key used for JWT signing."""

    JWT_ENCRYPTION_ALGORITHM: str = field(default_factory=lambda: "HS256")
    """JWT Encryption Algorithm"""

    CSRF_COOKIE_NAME: str = field(
        default_factory=get_env("CSRF_COOKIE_NAME", "XSRF-TOKEN"))
    """CSRF Cookie Name"""

    CSRF_COOKIE_SECURE: bool = field(
        default_factory=get_env("CSRF_COOKIE_SECURE", False))
    """CSRF Secure Cookie"""
```

### Configuration Management

Settings are loaded from environment variables and `.env` files:

```python
@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    return Settings.from_env()
```

### Example Environment Configuration

```bash
# .env file
SECRET_KEY=your-super-secret-jwt-signing-key-here
JWT_ENCRYPTION_ALGORITHM=HS256
CSRF_COOKIE_SECURE=true
```

## Token Storage and Transmission

### Token Transmission Methods

1. **Authorization Header** (Recommended):
   ```
   Authorization: Bearer <jwt_token>
   ```

2. **Cookie Storage** (Alternative):
   ```python
   # Set secure cookie
   response.set_cookie(
       key="access_token",
       value=token,
       httponly=True,
       secure=True,
       samesite="strict"
   )
   ```

### Client-Side Storage Options

1. **Memory Storage** (Most Secure):
   ```javascript
   let authToken = null;

   function setToken(token) {
       authToken = token;
   }
   ```

2. **Session Storage** (Good):
   ```javascript
   sessionStorage.setItem('authToken', token);
   ```

3. **Local Storage** (Less Secure):
   ```javascript
   localStorage.setItem('authToken', token);
   ```

### HTTP Client Implementation

```python
# Example HTTP client with JWT
import httpx

class AuthenticatedClient:
    def __init__(self, base_url: str, token: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"}
        )

    async def get(self, endpoint: str, **kwargs):
        return await self.client.get(endpoint, **kwargs)
```

### Frontend Integration

```typescript
// TypeScript example for JWT handling
class AuthService {
    private token: string | null = null;

    async login(email: string, password: string): Promise<string> {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        this.token = data.access_token;
        return this.token;
    }

    getAuthHeaders(): Record<string, string> {
        return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
    }
}
```

## JWT Troubleshooting and Debugging

### Common Issues and Solutions

#### 1. Token Not Valid

**Error**: `JWT token is not valid`

**Causes**:
- Expired token
- Invalid signature
- Modified token

**Solution**:
```python
# Check token expiration
import jwt
try:
    decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
    print(f"Token expires at: {datetime.fromtimestamp(decoded['exp'])}")
except jwt.ExpiredSignatureError:
    print("Token has expired")
```

#### 2. User Not Found

**Error**: `User not found or inactive`

**Causes**:
- User deleted
- User inactive
- User not verified

**Solution**:
```python
# Check user status
user = await users_service.get_one_or_none(email=token.sub)
if user:
    print(f"User active: {user.is_active}")
    print(f"User verified: {user.is_verified}")
```

#### 3. Authentication Header Missing

**Error**: `Authorization header missing`

**Causes**:
- Client not sending header
- Header format incorrect

**Solution**:
```python
# Verify header format
# Correct: Authorization: Bearer <token>
# Incorrect: Authorization: <token>
```

### Debugging Tools

#### 1. Token Decoder

```python
import jwt
from datetime import datetime

def debug_token(token: str, secret: str):
    """Debug JWT token contents."""
    try:
        decoded = jwt.decode(token, secret, algorithms=['HS256'])
        print("Token decoded successfully:")
        print(f"  Subject: {decoded['sub']}")
        print(f"  Issued At: {datetime.fromtimestamp(decoded['iat'])}")
        print(f"  Expires At: {datetime.fromtimestamp(decoded['exp'])}")
        print(f"  Time Remaining: {decoded['exp'] - datetime.now().timestamp()} seconds")
        return decoded
    except jwt.ExpiredSignatureError:
        print("Token has expired")
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")

# Usage
debug_token("your.jwt.token", "your-secret-key")
```

#### 2. Authentication Flow Tester

```python
import asyncio
import httpx

async def test_auth_flow(base_url: str, email: str, password: str):
    """Test complete authentication flow."""
    async with httpx.AsyncClient() as client:
        # Test login
        login_response = await client.post(
            f"{base_url}/api/auth/login",
            data={"username": email, "password": password}
        )

        if login_response.status_code != 200:
            print(f"Login failed: {login_response.text}")
            return

        token_data = login_response.json()
        token = token_data["access_token"]
        print(f"Login successful, token: {token[:20]}...")

        # Test protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = await client.get(
            f"{base_url}/api/auth/profile",
            headers=headers
        )

        if profile_response.status_code == 200:
            print("Protected endpoint access successful")
            print(f"User data: {profile_response.json()}")
        else:
            print(f"Protected endpoint failed: {profile_response.text}")

# Usage
asyncio.run(test_auth_flow("http://localhost:8000", "user@example.com", "password"))
```

### Logging Configuration

```python
# Enable JWT debugging in settings
LOG_LEVEL=DEBUG

# Custom JWT logging
import structlog
logger = structlog.get_logger()

async def current_user_from_token(token: Token, connection: ASGIConnection[Any, Any, Any, Any]) -> m.User | None:
    """Lookup current user from local JWT token with debugging."""
    logger.info("JWT token validation",
                email=token.sub,
                expires_at=token.exp)

    user = await service.get_one_or_none(email=token.sub)

    if user:
        logger.info("User found",
                    user_id=user.id,
                    is_active=user.is_active,
                    is_verified=user.is_verified)
    else:
        logger.warning("User not found", email=token.sub)

    return user if user and user.is_active and user.is_verified else None
```

### Testing JWT Authentication

#### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_jwt_authentication():
    """Test JWT token creation and validation."""
    from app.domain.accounts.guards import auth

    # Create test token
    token = auth.create_token(identifier="test@example.com")
    assert token is not None

    # Test token validation
    with patch('app.domain.accounts.guards.provide_users_service') as mock_service:
        mock_user = AsyncMock()
        mock_user.is_active = True
        mock_user.is_verified = True

        service_instance = AsyncMock()
        service_instance.get_one_or_none.return_value = mock_user
        mock_service.return_value.__anext__.return_value = service_instance

        # Create mock token object
        token_obj = type('Token', (), {'sub': 'test@example.com'})()

        user = await current_user_from_token(token_obj, None)
        assert user is not None
        assert user.is_active
        assert user.is_verified
```

#### Integration Tests

```python
@pytest.mark.asyncio
async def test_complete_auth_flow(client: AsyncClient):
    """Test complete authentication flow."""
    # Register user
    register_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }
    response = await client.post("/api/auth/register", json=register_data)
    assert response.status_code == 201

    # Login
    login_data = {
        "username": "test@example.com",
        "password": "testpassword123"
    }
    response = await client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200

    token_data = response.json()
    token = token_data["access_token"]

    # Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/auth/profile", headers=headers)
    assert response.status_code == 200

    profile_data = response.json()
    assert profile_data["email"] == "test@example.com"
```

### Performance Considerations

#### Database Optimization

```python
# Optimized user lookup with preloaded relationships
provide_users_service = create_service_provider(
    UserService,
    load=[
        selectinload(m.User.roles).options(
            joinedload(m.UserRole.role, innerjoin=True)),
        selectinload(m.User.oauth_accounts),
    ],
    error_messages={"duplicate_key": "This user already exists."},
)
```

#### Token Caching

```python
# Example token cache implementation
from functools import lru_cache
import time

@lru_cache(maxsize=1000)
def get_cached_user(token: str, cache_time: int):
    """Cache user lookup by token."""
    # Implement caching logic
    pass
```

### Security Audit Checklist

- [ ] Strong secret key generation
- [ ] HTTPS enforcement in production
- [ ] Token expiration configured appropriately
- [ ] Rate limiting on auth endpoints
- [ ] Input validation on all auth inputs
- [ ] Proper error handling without information leakage
- [ ] Audit logging for authentication events
- [ ] CSRF protection enabled
- [ ] Secure cookie configuration
- [ ] Regular secret key rotation

### Production Deployment Considerations

1. **Environment Variables**:
   ```bash
   # Production settings
   SECRET_KEY=$(openssl rand -hex 32)
   JWT_ENCRYPTION_ALGORITHM=HS256
   CSRF_COOKIE_SECURE=true
   ```

2. **Load Balancer Configuration**:
   ```nginx
   # Nginx configuration
   location /api/ {
       proxy_pass http://backend;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   ```

3. **Monitoring**:
   ```python
   # Add authentication metrics
   from prometheus_client import Counter

   auth_attempts = Counter('auth_attempts_total', 'Total authentication attempts', ['status'])

   async def login_with_metrics(self, data: AccountLogin) -> Response[OAuth2Login]:
       try:
           user = await users_service.authenticate(data.username, data.password)
           auth_attempts.labels(status='success').inc()
           return auth.login(user.email)
       except Exception:
           auth_attempts.labels(status='failure').inc()
           raise
   ```

This comprehensive JWT authentication implementation provides secure, scalable authentication for the Todo AI application while following modern security best practices and providing excellent developer experience through Litestar's built-in JWT support.