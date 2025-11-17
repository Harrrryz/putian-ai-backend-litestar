# REST API Reference

This comprehensive REST API reference provides detailed documentation for all endpoints in the Todo AI application built with Litestar framework.

## Table of Contents

1. [Authentication & Authorization](#authentication--authorization)
2. [Accounts & User Management API](#accounts--user-management-api)
3. [Todo Management API](#todo-management-api)
4. [Todo Agents & Chat API](#todo-agents--chat-api)
5. [Agent Sessions API](#agent-sessions-api)
6. [System Health & Monitoring API](#system-health--monitoring-api)
7. [API Request/Response Formats](#api-requestresponse-formats)
8. [Error Handling](#error-handling)
9. [Rate Limiting & Quotas](#rate-limiting--quotas)

## Authentication & Authorization

### Overview

The API uses JWT (JSON Web Token) based authentication with OAuth2 Password Bearer flow. All protected endpoints require a valid JWT token in the Authorization header.

### Authentication Flow

1. **Login**: Obtain JWT token via `/api/access/login`
2. **Include Token**: Add token to Authorization header for subsequent requests
3. **Token Validation**: Server validates token on each protected request

### Authorization Types

- **Public Access**: No authentication required
- **Authenticated User**: Valid JWT token required
- **Active User**: User must be active (not deactivated)
- **Verified User**: User must have verified email address
- **Superuser**: User must have superuser privileges

### HTTP Headers

```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Authentication Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/access/login` | POST | No | Authenticate user and obtain JWT token |
| `/api/access/logout` | POST | No | Logout user (client-side token removal) |
| `/api/access/signup` | POST | No | Register new user account |
| `/api/access/verify-email` | GET/POST | No | Verify user email address |

## Accounts & User Management API

### Authentication Endpoints

#### User Login

```http
POST /api/access/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### User Registration

```http
POST /api/access/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "name": "John Doe",
  "is_superuser": false,
  "is_active": true,
  "is_verified": false,
  "has_password": true,
  "roles": [],
  "oauthAccounts": []
}
```

#### Email Verification

```http
POST /api/access/verify-email
Content-Type: application/x-www-form-urlencoded

token=verification_token_here
```

**Response:**
```json
{
  "message": "Email verified successfully"
}
```

#### Resend Verification Email

```http
POST /api/access/resend-verification
Content-Type: application/x-www-form-urlencoded

email=user@example.com
```

**Response:**
```json
{
  "message": "If an account with this email exists, a verification email will be sent."
}
```

#### User Logout

```http
POST /api/access/logout
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "OK"
}
```

#### Get User Profile

```http
GET /api/me
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "name": "John Doe",
  "is_superuser": false,
  "is_active": true,
  "is_verified": true,
  "has_password": true,
  "roles": [
    {
      "roleId": "456e7890-e89b-12d3-a456-426614174001",
      "roleSlug": "user",
      "roleName": "User",
      "assignedAt": "2023-12-01T10:00:00Z"
    }
  ],
  "oauthAccounts": []
}
```

### User Management (Superuser Only)

#### List Users

```http
GET /api/users?page=1&limit=20&search=john&sortField=name&sortOrder=asc
Authorization: Bearer <admin_jwt_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `search`: Search in name and email fields
- `sortField`: Field to sort by (name, email, createdAt, updatedAt)
- `sortOrder`: Sort order (asc, desc)
- `createdAt`: Filter by creation date (ISO format)
- `updatedAt`: Filter by update date (ISO format)

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "user@example.com",
      "name": "John Doe",
      "is_superuser": false,
      "is_active": true,
      "is_verified": true,
      "hasPassword": true,
      "roles": [],
      "oauthAccounts": []
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20,
  "totalPages": 1
}
```

#### Get User

```http
GET /api/users/{user_id}
Authorization: Bearer <admin_jwt_token>
```

#### Create User

```http
POST /api/users
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "name": "New User",
  "isSuperuser": false,
  "isActive": true,
  "isVerified": false
}
```

#### Update User

```http
PATCH /api/users/{user_id}
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "name": "Updated Name",
  "isActive": true
}
```

#### Delete User

```http
DELETE /api/users/{user_id}
Authorization: Bearer <admin_jwt_token>
```

### User Role Management (Superuser Only)

#### Assign Role to User

```http
POST /api/roles/{role_slug}/assign
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "userName": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Successfully assigned the 'user' role to user@example.com."
}
```

#### Revoke Role from User

```http
POST /api/roles/{role_slug}/revoke
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "userName": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Removed the 'user' role from User user@example.com."
}
```

## Todo Management API

All todo management endpoints require authentication and active user status.

### List Todos

```http
GET /todos/?page=1&limit=40&search=project&sortField=createdTime&sortOrder=desc&startTimeFrom=2023-12-01T00:00:00Z&startTimeTo=2023-12-31T23:59:59Z
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 40)
- `search`: Search in todo item field
- `sortField`: Field to sort by (createdTime, updatedAt, item)
- `sortOrder`: Sort order (asc, desc)
- `startTimeFrom`: Filter todos with start_time after this datetime
- `startTimeTo`: Filter todos with start_time before this datetime
- `endTimeFrom`: Filter todos with end_time after this datetime
- `endTimeTo`: Filter todos with end_time before this datetime

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "item": "Complete project documentation",
      "description": "Write comprehensive documentation for the new feature",
      "createdTime": "2023-12-01T10:00:00Z",
      "alarmTime": "2023-12-15T09:00:00Z",
      "startTime": "2023-12-10T09:00:00Z",
      "endTime": "2023-12-15T17:00:00Z",
      "importance": "high",
      "userId": "123e4567-e89b-12d3-a456-426614174001",
      "tags": ["work", "documentation"]
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 40,
  "totalPages": 1
}
```

### Create Todo

```http
POST /todos/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "item": "Complete project documentation",
  "description": "Write comprehensive documentation for the new feature",
  "alarmTime": "2023-12-15T09:00:00Z",
  "startTime": "2023-12-10T09:00:00Z",
  "endTime": "2023-12-15T17:00:00Z",
  "importance": "high",
  "tags": ["work", "documentation"]
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "item": "Complete project documentation",
  "description": "Write comprehensive documentation for the new feature",
  "createdTime": "2023-12-01T10:00:00Z",
  "alarmTime": "2023-12-15T09:00:00Z",
  "startTime": "2023-12-10T09:00:00Z",
  "endTime": "2023-12-15T17:00:00Z",
  "importance": "high",
  "userId": "123e4567-e89b-12d3-a456-426614174001",
  "tags": ["work", "documentation"]
}
```

### Get Todo

```http
GET /todos/{todo_id}
Authorization: Bearer <jwt_token>
```

### Update Todo

```http
PATCH /todos/{todo_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "item": "Updated todo item",
  "description": "Updated description",
  "importance": "medium"
}
```

### Delete Todo

```http
DELETE /todos/{todo_id}
Authorization: Bearer <jwt_token>
```

### Create Tag

```http
POST /todos/create_tag
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "urgent",
  "color": "#ff0000",
  "todoId": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response:**
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174002",
  "name": "urgent",
  "color": "#ff0000",
  "userId": "123e4567-e89b-12d3-a456-426614174001"
}
```

### Delete Tag

```http
DELETE /todos/delete_tag/{tag_id}
Authorization: Bearer <jwt_token>
```

### List Tags

```http
GET /todos/tags?page=1&limit=20
Authorization: Bearer <jwt_token>
```

## Todo Agents & Chat API

AI-powered todo management endpoints with rate limiting and usage quotas.

### Create Todo with AI Agent

```http
POST /api/todos/agent-create
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "I need to prepare for tomorrow's important presentation at 2 PM"
    }
  ],
  "sessionId": "user_123_todo_agent",
  "sessionName": "Presentation Planning"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "I've created a todo for your presentation preparation. I've set it for tomorrow at 2 PM with high importance.",
  "agentResponse": [
    {
      "role": "user",
      "content": "I need to prepare for tomorrow's important presentation at 2 PM",
      "timestamp": "2023-12-01T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "I've created a todo for your presentation preparation. I've set it for tomorrow at 2 PM with high importance.",
      "timestamp": "2023-12-01T10:00:01Z"
    }
  ]
}
```

### Stream Todo Agent Response

```http
POST /api/todos/agent-create/stream
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Help me plan my week"
    }
  ],
  "sessionId": "user_123_week_planning"
}
```

**Response (Server-Sent Events):**
```
event: message
data: {"type": "content", "content": "I'll help you plan your week"}

event: todo_created
data: {"id": "...", "item": "Weekly planning session"}

event: completed
data: {"status": "success", "message": "Week planning completed"}
```

### List Agent Sessions

```http
GET /api/todos/agent-sessions
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "sessions": [
    "user_123_todo_agent",
    "user_123_week_planning"
  ]
}
```

### Create New Agent Session

```http
POST /api/todos/agent-sessions/new
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "message": "New session created successfully",
  "sessionId": "session_123_20231201_143000"
}
```

### Get Session History

```http
GET /api/todos/agent-sessions/{session_id}/history?limit=50
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "sessionId": "user_123_todo_agent",
  "history": [
    {
      "role": "user",
      "content": "I need to prepare for tomorrow's presentation",
      "timestamp": "2023-12-01T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "I've created a todo for your presentation preparation",
      "timestamp": "2023-12-01T10:00:01Z"
    }
  ]
}
```

### Clear Session History

```http
DELETE /api/todos/agent-sessions/{session_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Session user_123_todo_agent history cleared successfully"
}
```

### Get Usage Statistics

```http
GET /api/todos/usage-stats
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "currentMonth": "2023-12",
  "usageCount": 45,
  "monthlyLimit": 200,
  "remainingQuota": 155,
  "resetDate": "2024-01-01T00:00:00Z"
}
```

## Agent Sessions API

Persistent conversation sessions for AI agent interactions.

### List Agent Sessions

```http
GET /api/agent-sessions?page=1&limit=20&search=planning&sortField=createdAt&sortOrder=desc
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "sessionId": "session_123_20231201_143000",
      "sessionName": "Project Planning",
      "description": "Planning session for new project",
      "isActive": true,
      "userId": "123e4567-e89b-12d3-a456-426614174001",
      "agentName": "TodoAssistant",
      "agentInstructions": "Help user manage their todos effectively",
      "createdAt": "2023-12-01T14:30:00Z",
      "updatedAt": "2023-12-01T15:45:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20,
  "totalPages": 1
}
```

### Create Agent Session

```http
POST /api/agent-sessions
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "sessionId": "weekly_planning_2023_48",
  "sessionName": "Weekly Planning",
  "description": "Session for weekly todo planning and organization",
  "isActive": true,
  "agentName": "TodoAssistant",
  "agentInstructions": "Focus on helping user organize their weekly tasks"
}
```

### Get Agent Session

```http
GET /api/agent-sessions/{session_id}
Authorization: Bearer <jwt_token>
```

### Update Agent Session

```http
PATCH /api/agent-sessions/{session_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "sessionName": "Updated Session Name",
  "description": "Updated description",
  "isActive": false
}
```

### Delete Agent Session

```http
DELETE /api/agent-sessions/{session_id}
Authorization: Bearer <jwt_token>
```

### Activate Agent Session

```http
PUT /api/agent-sessions/{session_id}/activate
Authorization: Bearer <jwt_token>
```

### Deactivate Agent Session

```http
PUT /api/agent-sessions/{session_id}/deactivate
Authorization: Bearer <jwt_token>
```

### Agent Conversation

```http
POST /api/agent-sessions/conversation
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "I need help organizing my tasks for today"
    }
  ],
  "sessionId": "daily_planning_session",
  "sessionName": "Daily Planning"
}
```

**Response:**
```json
{
  "sessionId": "daily_planning_session",
  "sessionUuid": "123e4567-e89b-12d3-a456-426614174000",
  "response": "I'd be happy to help you organize your tasks for today! Let me check your current todos and suggest an optimal schedule.",
  "messagesCount": 2,
  "sessionActive": true
}
```

## Session Messages API

Manage individual messages within agent sessions.

### List Session Messages

```http
GET /api/sessions/{session_id}/messages?page=1&limit=50&sortField=createdAt&sortOrder=asc
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "role": "user",
      "content": "I need help organizing my tasks for today",
      "toolCallId": null,
      "toolName": null,
      "extraData": null,
      "sessionId": "456e7890-e89b-12d3-a456-426614174001",
      "createdAt": "2023-12-01T10:00:00Z",
      "updatedAt": "2023-12-01T10:00:00Z"
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174002",
      "role": "assistant",
      "content": "I'd be happy to help you organize your tasks for today!",
      "toolCallId": null,
      "toolName": null,
      "extraData": null,
      "sessionId": "456e7890-e89b-12d3-a456-426614174001",
      "createdAt": "2023-12-01T10:00:01Z",
      "updatedAt": "2023-12-01T10:00:01Z"
    }
  ],
  "total": 2,
  "page": 1,
  "pageSize": 50,
  "totalPages": 1
}
```

### Create Session Message

```http
POST /api/sessions/{session_id}/messages
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "role": "user",
  "content": "What's the priority of my tasks today?",
  "toolCallId": null,
  "toolName": null,
  "extraData": null
}
```

### Get Session Message

```http
GET /api/sessions/{session_id}/messages/{message_id}
Authorization: Bearer <jwt_token>
```

### Update Session Message

```http
PATCH /api/sessions/{session_id}/messages/{message_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "content": "Updated message content",
  "extraData": "{\"priority\": \"high\"}"
}
```

### Delete Session Message

```http
DELETE /api/sessions/{session_id}/messages/{message_id}
Authorization: Bearer <jwt_token>
```

### Clear Session Messages

```http
DELETE /api/sessions/{session_id}/messages/clear
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "deletedCount": 15
}
```

## System Health & Monitoring API

### System Health Check

```http
GET /health
```

**Response (Healthy):**
```json
{
  "databaseStatus": "online",
  "app": "Todo AI",
  "version": "1.0.0"
}
```

**Response (Unhealthy):**
```json
{
  "databaseStatus": "offline",
  "app": "Todo AI",
  "version": "1.0.0"
}
```

## API Request/Response Formats

### Request Formats

#### JSON Requests

```http
Content-Type: application/json

{
  "field1": "value1",
  "field2": "value2",
  "nestedObject": {
    "subField": "subValue"
  },
  "arrayField": ["item1", "item2"]
}
```

#### Form Data Requests

```http
Content-Type: application/x-www-form-urlencoded

field1=value1&field2=value2
```

### Response Formats

#### Success Response

```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Example"
  },
  "message": "Operation completed successfully"
}
```

#### Paginated Response

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pageSize": 20,
  "totalPages": 5
}
```

#### Error Response

```json
{
  "detail": "Error description",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR"
}
```

### Data Types

| Type | Format | Example |
|------|--------|---------|
| UUID | String | `"123e4567-e89b-12d3-a456-426614174000"` |
| DateTime | ISO 8601 | `"2023-12-01T10:00:00Z"` |
| Boolean | true/false | `true` |
| Importance | Enum | `"none" | "low" | "medium" | "high"` |
| MessageRole | Enum | `"user" | "assistant" | "system"` |

## Error Handling

### HTTP Status Codes

| Status Code | Description | Usage |
|-------------|-------------|-------|
| 200 | OK | Successful operation |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
  "detail": "Human-readable error message",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR",
  "field_errors": {
    "email": "Invalid email format",
    "password": "Password must be at least 6 characters"
  }
}
```

### Common Error Types

#### Authentication Errors
- `INVALID_CREDENTIALS`: Invalid username or password
- `TOKEN_EXPIRED`: JWT token has expired
- `TOKEN_INVALID`: JWT token is invalid

#### Authorization Errors
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `ACCOUNT_INACTIVE`: User account is not active
- `ACCOUNT_NOT_VERIFIED`: User email is not verified

#### Validation Errors
- `VALIDATION_ERROR`: Request data validation failed
- `MISSING_REQUIRED_FIELD`: Required field is missing
- `INVALID_FORMAT`: Field format is invalid

#### Resource Errors
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `RESOURCE_CONFLICT`: Resource already exists or conflicts with current state
- `OPERATION_NOT_ALLOWED`: Operation is not permitted

#### Rate Limiting Errors
- `RATE_LIMIT_EXCEEDED`: User has exceeded their usage quota

## Rate Limiting & Quotas

### Overview

The API implements rate limiting and usage quotas for AI agent endpoints to ensure fair usage and system stability.

### Rate Limits

| Endpoint Type | Limit | Period | Description |
|---------------|-------|--------|-------------|
| Agent Chat | 200 requests | Per month | Per authenticated user |
| Session Creation | 50 requests | Per month | Per authenticated user |
| Standard API | No limit | - | Non-AI endpoints |

### Quota Headers

Rate-limited responses include quota information:

```http
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 155
X-RateLimit-Reset: 1704067200
X-RateLimit-Reset-Date: 2024-01-01T00:00:00Z
```

### Rate Limit Exceeded Response

```json
{
  "status": "error",
  "message": "Rate limit exceeded. Used 200/200 requests this month. Quota resets on 2024-01-01.",
  "errorCode": "RATE_LIMIT_EXCEEDED",
  "currentUsage": 200,
  "monthlyLimit": 200,
  "resetDate": "2024-01-01T00:00:00Z",
  "remainingQuota": 0
}
```

### Usage Monitoring

Users can check their current usage status via the `/api/todos/usage-stats` endpoint to monitor their quota consumption and reset dates.

## API Examples

### Complete User Workflow

```bash
# 1. Register new user
curl -X POST http://localhost:8000/api/access/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "name": "John Doe"
  }'

# 2. Login
curl -X POST http://localhost:8000/api/access/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword123"

# 3. Create todo
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -X POST http://localhost:8000/todos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item": "Complete project documentation",
    "description": "Write comprehensive documentation",
    "startTime": "2023-12-10T09:00:00Z",
    "endTime": "2023-12-15T17:00:00Z",
    "importance": "high",
    "tags": ["work", "documentation"]
  }'

# 4. Use AI agent
curl -X POST http://localhost:8000/api/todos/agent-create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Help me organize my work tasks for this week"
      }
    ],
    "sessionId": "weekly_planning"
  }'
```

### Streaming Response Example

```javascript
// Client-side JavaScript for streaming responses
const eventSource = new EventSource(
  '/api/todos/agent-create/stream',
  {
    headers: {
      'Authorization': 'Bearer ' + token
    }
  }
);

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received:', data);

  if (event.event === 'todo_created') {
    // Handle todo creation
    addTodoToList(data);
  }
};

eventSource.onerror = function(event) {
  console.error('Stream error:', event);
  eventSource.close();
};
```

This comprehensive REST API reference provides complete documentation for all endpoints in the Todo AI application, including authentication, user management, todo operations, AI agent interactions, session management, and system monitoring.