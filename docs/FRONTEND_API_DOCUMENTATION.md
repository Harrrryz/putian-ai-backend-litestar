# Frontend API Documentation

This document provides a comprehensive guide for frontend developers to integrate with the Putian AI Todo Backend API built with Litestar.

## Overview

The API is organized into several domains:
- **System** - Health checks and system status
- **Accounts** - User authentication and management
- **Todo** - Todo item and tag management
- **Agent Sessions** - AI agent conversation sessions
- **Todo Agents** - AI-powered todo management
- **Session Messages** - Individual messages within agent sessions

## Base URL
All API endpoints are relative to your backend server URL (e.g., `http://localhost:8000`)

## Authentication
The API uses JWT-based authentication. Include the JWT token in your requests via cookies or headers as configured.

---

## System Domain

### Health Check
**GET** `/health`
- **Operation ID**: `SystemHealth`
- **Description**: Check the health of backend components including database
- **Authentication**: Not required
- **Response**: 
  ```typescript
  {
    database_status: "online" | "offline",
    healthy: boolean
  }
  ```

---

## Accounts Domain

### Authentication Endpoints

#### Login
**POST** `/api/access/login`
- **Operation ID**: `AccountLogin`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Authentication**: Not required
- **Body**:
  ```typescript
  {
    username: string,
    password: string
  }
  ```
- **Response**: JWT token and user session

#### Logout  
**POST** `/api/access/logout`
- **Operation ID**: `AccountLogout`
- **Authentication**: Not required
- **Response**: Success message and cookie clearing

#### Register
**POST** `/api/access/signup`
- **Operation ID**: `AccountRegister`
- **Authentication**: Not required
- **Body**:
  ```typescript
  {
    email: string,
    password: string,
    name?: string
    // Additional user fields
  }
  ```
- **Response**: Created user object

#### Get Profile
**GET** `/api/me`
- **Operation ID**: `AccountProfile`
- **Authentication**: Required (active user)
- **Response**: Current user profile

### User Management Endpoints (Admin Only)

#### List Users
**GET** `/api/users`
- **Operation ID**: `ListUsers`
- **Authentication**: Required (superuser)
- **Query Parameters**:
  - `limit`: number (default: 20)
  - `offset`: number (default: 0)
  - `search`: string (searches name, email)
  - `created_at`: date filter
  - `updated_at`: date filter
  - `sort_field`: "name" | "email" | "created_at"
  - `sort_order`: "asc" | "desc"
- **Response**: Paginated list of users

#### Get User
**GET** `/api/users/{user_id}`
- **Operation ID**: `GetUser`
- **Authentication**: Required (superuser)
- **Parameters**: `user_id` (UUID)
- **Response**: User object

#### Create User
**POST** `/api/users`
- **Operation ID**: `CreateUser`
- **Authentication**: Required (superuser)
- **Body**: User creation data
- **Response**: Created user object

#### Update User
**PATCH** `/api/users/{user_id}`
- **Operation ID**: `UpdateUser`
- **Authentication**: Required (superuser)
- **Parameters**: `user_id` (UUID)
- **Body**: Partial user data
- **Response**: Updated user object

#### Delete User
**DELETE** `/api/users/{user_id}`
- **Operation ID**: `DeleteUser`
- **Authentication**: Required (superuser)
- **Parameters**: `user_id` (UUID)
- **Response**: No content

### Role Management Endpoints (Admin Only)

#### Assign Role
**POST** `/api/roles/{role_slug}/assign`
- **Operation ID**: `AssignUserRole`
- **Authentication**: Required (superuser)
- **Parameters**: `role_slug` (string)
- **Body**:
  ```typescript
  {
    user_name: string // User email
  }
  ```
- **Response**: Success message

#### Revoke Role
**POST** `/api/roles/{role_slug}/revoke`
- **Operation ID**: `RevokeUserRole`
- **Authentication**: Required (superuser)
- **Parameters**: `role_slug` (string)
- **Body**: Revoke data
- **Response**: Success message

---

## Todo Domain

### Todo Management

#### List Todos
**GET** `/todos/`
- **Operation ID**: `list_todos`
- **Authentication**: Required
- **Query Parameters**:
  - `limit`: number (default: 20)
  - `offset`: number (default: 0)
  - `search`: string (searches item field)
  - `created_at`: date filter
  - `updated_at`: date filter
  - `sort_field`: "created_time" | "item"
  - `sort_order`: "asc" | "desc"
- **Response**: Paginated list of user's todos

#### Create Todo
**POST** `/todos/`
- **Operation ID**: `create_todo`
- **Authentication**: Required
- **Body**:
  ```typescript
  {
    item: string,
    description?: string,
    alarm_time?: datetime,
    start_time: datetime,
    end_time: datetime,
    importance?: "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    tags?: string[]
  }
  ```
- **Response**: Created todo object

#### Get Todo
**GET** `/todos/{todo_id}`
- **Operation ID**: `get_todo`
- **Authentication**: Required
- **Parameters**: `todo_id` (UUID)
- **Response**: Todo object or error message

#### Update Todo
**PATCH** `/todos/{todo_id}`
- **Operation ID**: `update_todo`
- **Authentication**: Required
- **Parameters**: `todo_id` (UUID)
- **Body**: Partial todo data
- **Response**: Updated todo object or error message

#### Delete Todo
**DELETE** `/todos/{todo_id}`
- **Operation ID**: `delete_todo`
- **Authentication**: Required
- **Parameters**: `todo_id` (UUID)
- **Response**: Deleted todo object or error message

### Tag Management

#### List Tags
**GET** `/todos/tags`
- **Operation ID**: `list_tags`
- **Authentication**: Required
- **Query Parameters**: Same filtering as todos
- **Response**: Paginated list of user's tags

#### Create Tag
**POST** `/todos/create_tag`
- **Operation ID**: `create_tag`
- **Authentication**: Required
- **Body**:
  ```typescript
  {
    name: string,
    color: string,
    todo_id?: UUID // Optional: associate with existing todo
  }
  ```
- **Response**: Created tag object

#### Delete Tag
**DELETE** `/todos/delete_tag/{tag_id}`
- **Operation ID**: `delete_tag`
- **Authentication**: Required
- **Parameters**: `tag_id` (UUID)
- **Response**: Deleted tag object or error message

---

## Agent Sessions Domain

### Session Management

#### List Agent Sessions
**GET** `/api/agent-sessions`
- **Operation ID**: `ListAgentSessions`
- **Authentication**: Required
- **Query Parameters**:
  - `limit`: number (default: 20)
  - `offset`: number (default: 0)
  - `search`: string (searches session_name)
  - `created_at`: date filter
  - `updated_at`: date filter
  - `sort_field`: "created_at" | "session_name"
  - `sort_order`: "desc" | "asc" (default: desc)
- **Response**: Paginated list of user's agent sessions

#### Create Agent Session
**POST** `/api/agent-sessions`
- **Operation ID**: `CreateAgentSession`
- **Authentication**: Required
- **Body**:
  ```typescript
  {
    session_id: string, // Unique identifier (1-255 chars)
    session_name?: string, // Human-readable name
    description?: string,
    agent_name?: string,
    agent_instructions?: string
  }
  ```
- **Response**: Created agent session object

#### Get Agent Session
**GET** `/api/agent-sessions/{session_id}`
- **Operation ID**: `GetAgentSession`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Response**: Agent session object

#### Update Agent Session
**PATCH** `/api/agent-sessions/{session_id}`
- **Operation ID**: `UpdateAgentSession`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Body**: Partial session data
- **Response**: Updated agent session object

#### Delete Agent Session
**DELETE** `/api/agent-sessions/{session_id}`
- **Operation ID**: `DeleteAgentSession`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Response**: No content

### Session State Management

#### Activate Session
**PUT** `/api/agent-sessions/{session_id}/activate`
- **Operation ID**: `ActivateAgentSession`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Response**: Updated session object

#### Deactivate Session
**PUT** `/api/agent-sessions/{session_id}/deactivate`
- **Operation ID**: `DeactivateAgentSession`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Response**: Updated session object

#### Clear Session Messages
**DELETE** `/api/agent-sessions/{session_id}/clear-messages`
- **Operation ID**: `ClearSessionMessages`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Response**: Success message

### Conversation Endpoint

#### Start Conversation
**POST** `/api/agent-sessions/conversation`
- **Operation ID**: `StartConversation`
- **Authentication**: Required
- **Body**:
  ```typescript
  {
    session_id: string,
    message: string,
    session_name?: string,
    agent_instructions?: string
  }
  ```
- **Response**: Agent response with conversation context

---

## Session Messages Domain

#### List Session Messages
**GET** `/api/agent-sessions/{session_id}/messages`
- **Operation ID**: `ListSessionMessages`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Query Parameters**:
  - `limit`: number (default: 50)
  - `offset`: number (default: 0)
  - `search`: string (searches content)
  - `sort_field`: "created_at"
  - `sort_order`: "asc" | "desc" (default: asc)
- **Response**: Paginated list of session messages

#### Create Session Message
**POST** `/api/agent-sessions/{session_id}/messages`
- **Operation ID**: `CreateSessionMessage`
- **Authentication**: Required
- **Parameters**: `session_id` (UUID)
- **Body**:
  ```typescript
  {
    role: "user" | "assistant" | "system",
    content: string,
    metadata?: any
  }
  ```
- **Response**: Created message object

#### Get Session Message
**GET** `/api/agent-sessions/{session_id}/messages/{message_id}`
- **Operation ID**: `GetSessionMessage`
- **Authentication**: Required
- **Parameters**: 
  - `session_id` (UUID)
  - `message_id` (UUID)
- **Response**: Message object

#### Update Session Message
**PATCH** `/api/agent-sessions/{session_id}/messages/{message_id}`
- **Operation ID**: `UpdateSessionMessage`
- **Authentication**: Required
- **Parameters**: 
  - `session_id` (UUID)
  - `message_id` (UUID)
- **Body**: Partial message data
- **Response**: Updated message object

#### Delete Session Message
**DELETE** `/api/agent-sessions/{session_id}/messages/{message_id}`
- **Operation ID**: `DeleteSessionMessage`
- **Authentication**: Required
- **Parameters**: 
  - `session_id` (UUID)
  - `message_id` (UUID)
- **Response**: No content

---

## Todo Agents Domain

### AI-Powered Todo Management

#### Create Todo with AI Agent
**POST** `/api/todos/agent-create`
- **Operation ID**: `agent_create_todo`
- **Authentication**: Required
- **Body**:
  ```typescript
  {
    session_id?: string, // Optional: if not provided, auto-generated
    session_name?: string, // Optional: defaults to "Todo Management Chat"
    messages: Array<{
      role: "user" | "assistant" | "system",
      content: string
    }>
  }
  ```
- **Response**:
  ```typescript
  {
    status: "success" | "error",
    message: string,
    agent_response: Array<{
      role: string,
      content: string,
      timestamp?: datetime
    }>
  }
  ```

#### List Agent Sessions
**GET** `/api/todos/agent-sessions`
- **Operation ID**: `list_agent_sessions`
- **Authentication**: Required
- **Response**: List of todo agent sessions

#### Get Session History
**GET** `/api/todos/agent-sessions/{session_id}/history`
- **Operation ID**: `get_session_history`
- **Authentication**: Required
- **Parameters**: `session_id` (string)
- **Response**: Conversation history for the session

#### Clear Agent Session
**DELETE** `/api/todos/agent-sessions/{session_id}`
- **Operation ID**: `clear_agent_session`
- **Authentication**: Required
- **Parameters**: `session_id` (string)
- **Response**: Success message

---

## Data Models

### User
```typescript
interface User {
  id: UUID;
  email: string;
  name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: datetime;
  updated_at: datetime;
  roles?: UserRole[];
}
```

### Todo
```typescript
interface Todo {
  id: UUID;
  item: string;
  description?: string;
  created_time: datetime;
  alarm_time?: datetime;
  start_time: datetime;
  end_time: datetime;
  importance: "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  user_id: UUID;
  tags?: string[];
}
```

### Tag
```typescript
interface Tag {
  id: UUID;
  name: string;
  color: string;
  user_id: UUID;
  created_at: datetime;
  updated_at: datetime;
}
```

### Agent Session
```typescript
interface AgentSession {
  id: UUID;
  session_id: string;
  session_name?: string;
  description?: string;
  is_active: boolean;
  user_id: UUID;
  agent_name?: string;
  agent_instructions?: string;
  created_at: datetime;
  updated_at: datetime;
}
```

### Session Message
```typescript
interface SessionMessage {
  id: UUID;
  session_id: UUID;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: any;
  created_at: datetime;
  updated_at: datetime;
}
```

---

## Error Handling

The API returns standard HTTP status codes:
- **200**: Success
- **201**: Created
- **204**: No Content
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **422**: Validation Error
- **500**: Internal Server Error

Error responses typically include:
```typescript
{
  detail: string | Array<{
    type: string;
    loc: string[];
    msg: string;
  }>
}
```

---

## Pagination

List endpoints return paginated responses:
```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

---

## Authentication Headers

Include authentication in requests:
```typescript
// If using bearer tokens
headers: {
  'Authorization': 'Bearer <your-jwt-token>'
}

// Or rely on HTTP-only cookies set by the login endpoint
```

---

## Example Usage

### Creating a Todo with AI Agent
```typescript
const response = await fetch('/api/todos/agent-create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include', // Include cookies
  body: JSON.stringify({
    messages: [{
      role: 'user',
      content: 'Create a todo to finish the quarterly report by Friday'
    }],
    session_name: 'Work Planning'
  })
});

const result = await response.json();
// result.agent_response contains the conversation history
// The AI will have created the todo automatically
```

### Listing User's Todos
```typescript
const response = await fetch('/todos/?limit=10&offset=0&sort_field=created_time&sort_order=desc', {
  credentials: 'include'
});

const todos = await response.json();
// todos.items contains the todo array
// todos.total contains the total count
```

This documentation covers all the main endpoints and provides the necessary information for frontend integration with the Putian AI Todo Backend API.
