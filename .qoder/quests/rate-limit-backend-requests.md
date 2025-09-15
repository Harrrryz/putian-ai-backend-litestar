# Rate Limiting for Backend Agent Requests

## Overview

This design document outlines the implementation of a rate limiting system for AI agent requests in the Putian AI Todo Backend. The system will enforce a monthly quota of 200 agent requests per user to manage resource usage and prevent abuse while maintaining the existing OpenAI SDK integration.

The rate limiting system will be seamlessly integrated into the existing clean architecture pattern, using the domain-driven design approach already established in the codebase.

## Architecture

### System Integration Point

The rate limiting functionality will be integrated at the service layer, specifically intercepting calls to the `TodoAgentService.chat_with_agent` method. This approach ensures:

- Minimal disruption to existing OpenAI SDK integration
- Consistent rate limiting across all agent interaction endpoints
- Proper separation of concerns within the clean architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Frontend/API Client]
    end
    
    subgraph "Controller Layer"
        B[TodoAgentController]
    end
    
    subgraph "Service Layer"
        C[TodoAgentService]
        D[RateLimitService]
        E[TodoService]
        F[TagService]
    end
    
    subgraph "Repository Layer"
        G[UserUsageQuotaRepository]
        H[TodoRepository]
    end
    
    subgraph "Database Layer"
        I[(PostgreSQL)]
    end
    
    A --> B
    B --> C
    C --> D
    D --> G
    C --> E
    C --> F
    G --> I
    H --> I
    
    classDef rateLimit fill:#ffeb3b,stroke:#f57f17,stroke-width:2px
    class D,G rateLimit
```

### Rate Limiting Flow

```mermaid
sequenceDiagram
    participant C as Controller
    participant TS as TodoAgentService
    participant RL as RateLimitService
    participant DB as Database
    participant AI as OpenAI SDK
    
    C->>TS: chat_with_agent(user_id, message)
    TS->>RL: check_rate_limit(user_id)
    RL->>DB: get_user_quota(user_id, current_month)
    DB-->>RL: current_usage_count
    
    alt Usage within limit
        RL->>DB: increment_usage(user_id, current_month)
        RL-->>TS: rate_limit_passed
        TS->>AI: Runner.run(agent, message, session)
        AI-->>TS: ai_response
        TS-->>C: success_response
    else Usage exceeds limit
        RL-->>TS: RateLimitExceededException
        TS-->>C: rate_limit_error_response
    end
```

## Data Models & ORM Mapping

### UserUsageQuota Model

```mermaid
erDiagram
    USER {
        uuid id PK
        string email
        string name
        datetime created_at
        datetime updated_at
    }
    
    USER_USAGE_QUOTA {
        uuid id PK
        uuid user_id FK
        string month_year
        int usage_count
        datetime created_at
        datetime updated_at
    }
    
    USER ||--o{ USER_USAGE_QUOTA : "has many quotas"
```

The `UserUsageQuota` model will track monthly agent request usage:

- **user_id**: Foreign key reference to the User model
- **month_year**: String in format "YYYY-MM" to identify the tracking period
- **usage_count**: Number of agent requests made in the specified month
- **Unique constraint**: Combination of user_id and month_year ensures one record per user per month

## Business Logic Layer

### RateLimitService

The rate limiting service will provide the following core functionalities:

#### Core Methods

| Method | Purpose | Parameters | Returns |
|--------|---------|------------|---------|
| `check_and_increment_usage` | Validates and records agent request | user_id: UUID, session: AsyncSession | None (raises exception if limit exceeded) |
| `get_user_usage_stats` | Retrieves current usage statistics | user_id: UUID, session: AsyncSession | UsageStats object |
| `get_remaining_quota` | Calculates remaining requests for current month | user_id: UUID, session: AsyncSession | int |

#### Rate Limiting Logic

```mermaid
flowchart TD
    A[Agent Request] --> B[Get Current Month: YYYY-MM]
    B --> C[Query UserUsageQuota Table]
    C --> D{Record Exists?}
    D -->|No| E[Create New Record with count=1]
    D -->|Yes| F[Check Current Usage Count]
    F --> G{Usage < 200?}
    G -->|Yes| H[Increment Usage Count]
    G -->|No| I[Raise RateLimitExceededException]
    E --> J[Process Agent Request]
    H --> J
    I --> K[Return Error Response]
    J --> L[Return Success Response]
```

### Exception Handling

Custom exception class for rate limit violations:

```mermaid
classDiagram
    ApplicationError <|-- RateLimitExceededException
    
    class ApplicationError {
        +detail: str
        +__init__(detail: str)
    }
    
    class RateLimitExceededException {
        +user_id: UUID
        +current_usage: int
        +monthly_limit: int
        +reset_date: datetime
        +__init__(user_id, current_usage, monthly_limit, reset_date)
        +to_http_exception() HTTPException
    }
```

## API Integration

### Modified TodoAgentService

The existing `TodoAgentService.chat_with_agent` method will be enhanced to include rate limiting:

#### Before Rate Limiting
```python
async def chat_with_agent(self, user_id: str, message: str, session_id: str | None = None) -> str:
    # Direct processing without rate limiting
    # Set context and run agent
```

#### After Rate Limiting Integration
```python
async def chat_with_agent(self, user_id: str, message: str, session_id: str | None = None) -> str:
    # Rate limiting check before processing
    # Increment usage if within limits
    # Process agent request
    # Return response
```

### Response Schema Extensions

Enhanced error responses for rate limiting scenarios:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "error" for rate limit violations |
| `message` | string | Human-readable error message |
| `error_code` | string | "RATE_LIMIT_EXCEEDED" |
| `current_usage` | integer | Number of requests used this month |
| `monthly_limit` | integer | Maximum requests allowed per month (200) |
| `reset_date` | string | ISO datetime when quota resets |
| `remaining_quota` | integer | Requests remaining this month |

### Usage Statistics Endpoint

New endpoint for users to check their current usage:

```
GET /api/v1/todo-agents/usage-stats
```

Response structure:
```json
{
  "status": "success",
  "current_month": "2025-01",
  "usage_count": 45,
  "monthly_limit": 200,
  "remaining_quota": 155,
  "reset_date": "2025-02-01T00:00:00Z"
}
```

## Database Migration

### Migration Script Structure

```mermaid
graph LR
    A[Create Migration File] --> B[Add UserUsageQuota Table]
    B --> C[Create Indexes]
    C --> D[Add Foreign Key Constraints]
    D --> E[Add Unique Constraints]
```

Migration details:
- **Table**: `user_usage_quota`
- **Primary Key**: UUID-based ID following existing pattern
- **Indexes**: Composite index on (user_id, month_year) for efficient lookups
- **Foreign Key**: References user_account.id with CASCADE delete
- **Unique Constraint**: Prevents duplicate records for user-month combinations

## Integration with OpenAI SDK

### Preservation of Existing Functionality

The rate limiting implementation will maintain full compatibility with the existing OpenAI SDK integration:

#### Session Management
- **No changes** to SQLiteSession usage pattern
- **No changes** to conversation history persistence
- **No changes** to Runner.run() method calls

#### Tool Integration
- **No changes** to agent tool definitions
- **No changes** to tool context management
- **No changes** to tool implementation patterns

#### Agent Factory
- **No changes** to agent creation and configuration
- **No changes** to LiteLLM model integration

### Rate Limiting Integration Points

```mermaid
graph TD
    A[Controller Receives Request] --> B[Service Layer Entry Point]
    B --> C[Rate Limit Check]
    C --> D{Within Limits?}
    D -->|Yes| E[Increment Usage Counter]
    D -->|No| F[Throw Rate Limit Exception]
    E --> G[Existing OpenAI SDK Flow]
    G --> H[SQLiteSession Management]
    H --> I[Agent Tool Execution]
    I --> J[Conversation Persistence]
    J --> K[Return Response]
    F --> L[Return Rate Limit Error]
    
    classDef rateLimit fill:#ffeb3b,stroke:#f57f17,stroke-width:2px
    classDef openai fill:#10a37f,stroke:#0d8f6b,stroke-width:2px
    
    class C,E rateLimit
    class G,H,I,J openai
```

## Configuration Management

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_MONTHLY_QUOTA` | 200 | Maximum agent requests per user per month |
| `RATE_LIMIT_ENABLED` | true | Enable/disable rate limiting globally |

### Dependency Injection Updates

The rate limiting service will be integrated into the existing dependency injection system:

```mermaid
graph TD
    A[Application Container] --> B[TodoAgentService]
    A --> C[RateLimitService]
    A --> D[DatabaseSession]
    
    B --> C
    C --> D
    
    E[Controller] --> B
    F[Dependency Provider] --> A
```

## Testing Strategy

### Unit Tests

#### RateLimitService Tests
- Test quota enforcement logic
- Test usage counter increment
- Test month rollover behavior
- Test exception handling scenarios

#### Integration Points Tests
- Test service integration with TodoAgentService
- Test database operations
- Test error response formatting

### Test Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| First request of month | Creates new quota record, allows request |
| Request within limit | Increments counter, allows request |
| Request at limit (200th) | Increments to 200, allows request |
| Request over limit (201st) | Throws RateLimitExceededException |
| New month rollover | Creates new quota record for new month |
| Database unavailable | Graceful degradation or error handling |
| Invalid user ID | Appropriate error response |

### Performance Testing

- Load testing with concurrent requests from same user
- Verification of database query performance
- Memory usage analysis for quota tracking

## Error Handling & User Experience

### Error Response Strategy

```mermaid
graph TD
    A[Rate Limit Exceeded] --> B[Generate Detailed Error Response]
    B --> C[Include Current Usage Stats]
    C --> D[Include Reset Date Information]
    D --> E[Provide Helpful Guidance]
    E --> F[Log for Monitoring]
```

### User-Friendly Error Messages

- Clear explanation of the rate limit
- Information about when the quota resets
- Guidance on usage patterns
- Contact information for quota increase requests

## Security Considerations

### User Isolation
- Rate limits are enforced per user ID
- No cross-user quota sharing
- Secure user identification through existing authentication

### Quota Tampering Prevention
- Database-level constraints prevent manipulation
- Atomic increment operations ensure consistency
- Audit trail through created_at/updated_at timestamps

### DoS Protection
- Rate limiting itself prevents agent request flooding
- Database connection pooling protects against connection exhaustion
- Efficient indexing prevents slow queries under load

## Performance Optimization

### Database Query Optimization
- Composite index on (user_id, month_year) for fast lookups
- Prepared statements for repeated queries
- Connection pooling for concurrent access

### Caching Strategy
- Consider in-memory caching for frequently accessed quotas
- Cache invalidation on quota updates
- Redis integration for distributed scenarios (future enhancement)

### Memory Efficiency
- Minimal memory footprint for quota tracking
- Efficient data structures for usage statistics
- Cleanup of old quota records (optional retention policy)