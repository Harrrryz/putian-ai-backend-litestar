# Agent Session Management

This document provides comprehensive documentation for the Agent Session Management system in the todo application, covering session lifecycle, persistence, security, and performance optimization.

## Overview

The Agent Session Management system provides robust session handling for AI-powered conversations between users and the TodoAssistant agent. It enables persistent conversation history, multi-user isolation, and seamless integration with the todo management system.

## 1. Agent Session Model

### Core Model Definition

```python
class AgentSession(UUIDAuditBase):
    """Agent conversation sessions for OpenAI Agents SDK integration."""

    __tablename__ = "agent_session"
    __table_args__ = {"comment": "Agent conversation sessions"}
    __pii_columns__ = {"session_name", "session_id"}
```

### Session Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `id` | UUID | Primary key (inherited from UUIDAuditBase) | Auto-generated |
| `session_id` | String(255) | External session identifier | Indexed, required |
| `session_name` | String(255) | Human-readable session name | Optional |
| `description` | Text | Optional session description | Optional |
| `is_active` | Boolean | Session activation status | Default: True |
| `user_id` | UUID | Foreign key to user account | Required, CASCADE delete |
| `agent_name` | String(255) | AI agent name | Optional |
| `agent_instructions` | Text | Agent-specific instructions | Optional |
| `created_at` | DateTimeUTC | Session creation timestamp | Auto-generated |
| `updated_at` | DateTimeUTC | Last modification timestamp | Auto-updated |

### Database Schema

```sql
CREATE TABLE agent_session (
    id GUID PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    session_name VARCHAR(255),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    user_id GUID NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    agent_instructions TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_agent_session_session_id ON agent_session(session_id);
```

## 2. Session Message Model

### Core Message Definition

```python
class SessionMessage(UUIDAuditBase):
    """Individual messages within agent conversation sessions."""

    __tablename__ = "session_message"
    __table_args__ = {"comment": "Messages in agent conversation sessions"}
    __pii_columns__ = {"content", "extra_data"}
```

### Message Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `id` | UUID | Primary key | Auto-generated |
| `role` | Enum | Message role (USER, ASSISTANT, SYSTEM, TOOL) | Required |
| `content` | Text | Message content | Required |
| `tool_call_id` | String(255) | Tool call identifier | Optional |
| `tool_name` | String(255) | Name of tool used | Optional |
| `extra_data` | Text | Additional metadata as JSON | Optional |
| `session_id` | UUID | Foreign key to agent session | Required, CASCADE delete |
| `created_at` | DateTimeUTC | Message creation timestamp | Auto-generated |
| `updated_at` | DateTimeUTC | Last modification timestamp | Auto-updated |

### Message Roles

```python
class MessageRole(enum.Enum):
    """Message roles based on OpenAI Agents SDK format."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
```

## 3. Session Lifecycle Management

### Session Creation

#### Service Layer Implementation

```python
async def create_session(self, current_user: User, data: AgentSessionCreate) -> AgentSessionSchema:
    """Create a new agent session with automatic user assignment."""
    session_dict = data.to_dict()
    session_dict["user_id"] = current_user.id
    obj = await self.create(session_dict)
    return self.to_schema(schema_type=AgentSessionSchema, data=obj)
```

#### API Endpoint

```python
@post("/api/agent-sessions")
async def create_session(
    self,
    current_user: User,
    service: AgentSessionService,
    data: AgentSessionCreate,
) -> AgentSessionSchema:
    """Create a new agent session."""
    session_dict = data.to_dict()
    session_dict["user_id"] = current_user.id
    obj = await service.create(session_dict)
    return service.to_schema(schema_type=AgentSessionSchema, data=obj)
```

#### Example Session Creation

```python
session_data = {
    "session_id": "session_user123_20241213_143000",
    "session_name": "Task Planning Discussion",
    "description": "Discussion about weekly task planning",
    "agent_name": "TodoAssistant",
    "agent_instructions": TODO_SYSTEM_INSTRUCTIONS,
    "is_active": True
}
```

### Session Activation/Deactivation

#### Activation Flow

```python
async def activate_session(self, session_id: UUID, user_id: UUID) -> AgentSession | None:
    """Activate an agent session."""
    session = await self.get_one_or_none(
        m.AgentSession.id == session_id,
        m.AgentSession.user_id == user_id
    )
    if session:
        return await self.update(data={"is_active": True}, item_id=session_id)
    return None
```

#### API Endpoints

```python
@put("/api/agent-sessions/{session_id}/activate")
async def activate_session(self, session_id: UUID) -> AgentSessionSchema:
    """Activate an agent session."""

@put("/api/agent-sessions/{session_id}/deactivate")
async def deactivate_session(self, session_id: UUID) -> AgentSessionSchema:
    """Deactivate an agent session."""
```

### Session Termination

#### Soft Deletion Pattern

```python
async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
    """Delete an agent session (hard delete)."""
    # Verify ownership
    obj = await self.get(session_id)
    if obj.user_id != user_id:
        raise ValueError("Session not found")

    # Cascade delete handles messages automatically
    await self.delete(session_id)
```

## 4. Message History Persistence and Retrieval

### Message Storage

```python
async def create_message(
    self,
    session_id: UUID,
    role: MessageRole,
    content: str,
    tool_call_id: str = None,
    tool_name: str = None,
    extra_data: str = None
) -> SessionMessage:
    """Store a new message in the session."""
    message_data = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "extra_data": extra_data,
    }
    return await self.create(message_data)
```

### Message Retrieval Patterns

#### Paginated Message Listing

```python
@get("/api/agent-sessions/{session_id}/messages")
async def list_messages(
    self,
    session_id: UUID,
    filters: List[FilterTypes] = None
) -> OffsetPagination[SessionMessageSchema]:
    """List messages with pagination and filtering."""
    session_filter = m.SessionMessage.session_id == session_id
    results, total = await message_service.list_and_count(
        session_filter,
        *(filters or [])
    )
    return message_service.to_schema(
        data=results,
        total=total,
        schema_type=SessionMessageSchema
    )
```

#### Recent Messages Query

```python
async def get_recent_messages(
    self,
    session_id: UUID,
    limit: int = 10
) -> Sequence[SessionMessage]:
    """Get the most recent messages from a session."""
    messages, _ = await self.list_and_count(
        m.SessionMessage.session_id == session_id
    )
    # Sort by created_at in descending order and limit
    sorted_messages = sorted(
        messages,
        key=lambda x: x.created_at,
        reverse=True
    )[:limit]
    return list(reversed(sorted_messages))
```

### Message Count Tracking

```python
async def get_session_message_count(self, session_id: UUID) -> int:
    """Get the total number of messages in a session."""
    _, count = await self.list_and_count(
        m.SessionMessage.session_id == session_id
    )
    return count
```

## 5. Session State Management and Transitions

### State Machine Implementation

```python
class SessionState:
    """Session state management with transitions."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"

    # Valid transitions
    TRANSITIONS = {
        ACTIVE: [INACTIVE, TERMINATED],
        INACTIVE: [ACTIVE, TERMINATED],
        TERMINATED: []  # Terminal state
    }

    def can_transition(self, from_state: str, to_state: str) -> bool:
        """Check if state transition is allowed."""
        return to_state in self.TRANSITIONS.get(from_state, [])
```

### Session State Validation

```python
async def validate_session_state_transition(
    self,
    session: AgentSession,
    new_state: bool
) -> bool:
    """Validate session state transition."""
    current_state = "active" if session.is_active else "inactive"
    desired_state = "active" if new_state else "inactive"

    if not self.state_machine.can_transition(current_state, desired_state):
        raise ValueError(f"Invalid state transition: {current_state} -> {desired_state}")

    return True
```

## 6. Session Timeout and Cleanup Policies

### Configuration Settings

```python
# Configuration for session management
SESSION_SETTINGS = {
    "default_timeout": 3600,  # 1 hour in seconds
    "max_inactive_time": 86400,  # 24 hours
    "cleanup_interval": 3600,  # 1 hour
    "max_session_age": 604800,  # 7 days
}
```

### Session Cleanup Service

```python
class SessionCleanupService:
    """Background service for session maintenance."""

    async def cleanup_inactive_sessions(self) -> Dict[str, int]:
        """Clean up inactive sessions older than threshold."""
        from datetime import datetime, timedelta

        threshold = datetime.utcnow() - timedelta(
            seconds=SESSION_SETTINGS["max_inactive_time"]
        )

        # Find inactive sessions
        inactive_sessions = await self.session_service.list(
            m.AgentSession.is_active == False,
            m.AgentSession.updated_at < threshold
        )

        deleted_count = 0
        for session in inactive_sessions:
            await self.session_service.delete(session.id)
            deleted_count += 1

        return {"deleted_sessions": deleted_count}

    async def cleanup_old_sessions(self) -> Dict[str, int]:
        """Clean up sessions older than maximum age."""
        from datetime import datetime, timedelta

        threshold = datetime.utcnow() - timedelta(
            seconds=SESSION_SETTINGS["max_session_age"]
        )

        old_sessions = await self.session_service.list(
            m.AgentSession.created_at < threshold
        )

        deleted_count = 0
        for session in old_sessions:
            await self.session_service.delete(session.id)
            deleted_count += 1

        return {"deleted_sessions": deleted_count}
```

### Automated Cleanup Scheduling

```python
import asyncio
from datetime import datetime

class SessionMaintenanceScheduler:
    """Scheduler for periodic session maintenance tasks."""

    def __init__(self, cleanup_service: SessionCleanupService):
        self.cleanup_service = cleanup_service
        self.running = False

    async def start(self):
        """Start the maintenance scheduler."""
        self.running = True
        while self.running:
            try:
                # Run cleanup tasks
                cleanup_results = await self.cleanup_service.cleanup_inactive_sessions()
                await self.cleanup_service.cleanup_old_sessions()

                logger.info("Session cleanup completed", results=cleanup_results)

                # Wait for next cleanup interval
                await asyncio.sleep(SESSION_SETTINGS["cleanup_interval"])

            except Exception as e:
                logger.error("Session cleanup failed", error=str(e))
                await asyncio.sleep(60)  # Retry after 1 minute

    async def stop(self):
        """Stop the maintenance scheduler."""
        self.running = False
```

## 7. Session-based Context and Memory Management

### Conversation Context Loading

```python
async def load_conversation_context(
    self,
    session_id: UUID,
    context_window: int = 20
) -> List[Dict[str, Any]]:
    """Load conversation context for AI agent."""
    messages = await self.message_service.get_recent_messages(
        session_id,
        limit=context_window
    )

    context = []
    for message in messages:
        context.append({
            "role": message.role.value.lower(),
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
            "tool_call_id": message.tool_call_id,
            "tool_name": message.tool_name,
            "extra_data": json.loads(message.extra_data) if message.extra_data else None
        })

    return context
```

### Context Window Management

```python
class ContextWindowManager:
    """Manages conversation context window for efficient AI interaction."""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.token_estimator = TokenEstimator()

    async def get_optimal_context(
        self,
        session_id: UUID,
        additional_tokens: int = 0
    ) -> List[SessionMessage]:
        """Get optimal context within token limit."""
        messages = await self.message_service.get_by_session(session_id)

        context_messages = []
        used_tokens = additional_tokens

        # Process messages from most recent to oldest
        for message in reversed(messages):
            message_tokens = self.token_estimator.estimate_tokens(message.content)

            if used_tokens + message_tokens > self.max_tokens:
                break

            context_messages.insert(0, message)
            used_tokens += message_tokens

        return context_messages
```

### Session Memory Persistence

```python
class SessionMemoryManager:
    """Manages persistent memory for agent sessions."""

    async def save_session_memory(
        self,
        session_id: UUID,
        memory_data: Dict[str, Any]
    ) -> None:
        """Save session memory metadata."""
        memory_entry = {
            "session_id": session_id,
            "memory_key": "session_context",
            "memory_data": json.dumps(memory_data),
            "created_at": datetime.utcnow()
        }
        await self.session_memory_service.create(memory_entry)

    async def load_session_memory(self, session_id: UUID) -> Dict[str, Any]:
        """Load session memory metadata."""
        memories = await self.session_memory_service.list(
            m.SessionMemory.session_id == session_id
        )

        memory_data = {}
        for memory in memories:
            try:
                data = json.loads(memory.memory_data)
                memory_data[memory.memory_key] = data
            except json.JSONDecodeError:
                continue

        return memory_data
```

## 8. Multi-user Session Isolation

### User Ownership Verification

```python
async def verify_session_ownership(
    self,
    session_id: UUID,
    user_id: UUID
) -> bool:
    """Verify that a session belongs to the specified user."""
    session = await self.get_one_or_none(
        m.AgentSession.id == session_id,
        m.AgentSession.user_id == user_id
    )
    return session is not None
```

### Session Access Control

```python
class SessionAccessController:
    """Controls session access and permissions."""

    async def can_access_session(
        self,
        user: User,
        session_id: UUID,
        operation: str = "read"
    ) -> bool:
        """Check if user can perform operation on session."""
        session = await self.session_service.get(session_id)

        # Verify ownership
        if session.user_id != user.id:
            return False

        # Check session-specific permissions
        if operation == "write" and not session.is_active:
            return False

        return True

    async def can_access_message(
        self,
        user: User,
        message_id: UUID,
        operation: str = "read"
    ) -> bool:
        """Check if user can access specific message."""
        message = await self.message_service.get(message_id)

        # Verify session ownership
        return await self.can_access_session(user, message.session_id, operation)
```

### Row-Level Security

```python
# Dependency provider with user filtering
provide_agent_session_service = create_service_provider(
    AgentSessionService,
    load=[
        joinedload(m.AgentSession.user, innerjoin=True),
        selectinload(m.AgentSession.messages),
    ],
    error_messages={
        "duplicate_key": "Agent session with this session_id already exists for this user.",
        "integrity": "Agent session operation failed.",
    },
)

# Service layer ensures user isolation
async def get_by_user(self, user_id: UUID) -> Sequence[AgentSession]:
    """Get all agent sessions for a specific user."""
    sessions, _ = await self.list_and_count(
        m.AgentSession.user_id == user_id
    )
    return sessions
```

## 9. Session Analytics and Monitoring

### Session Metrics Collection

```python
class SessionAnalyticsService:
    """Service for collecting and analyzing session metrics."""

    async def get_session_statistics(
        self,
        user_id: UUID = None
    ) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        base_query = []
        if user_id:
            base_query.append(m.AgentSession.user_id == user_id)

        # Session counts
        total_sessions = await self.session_service.count(*base_query)
        active_sessions = await self.session_service.count(
            *base_query,
            m.AgentSession.is_active == True
        )

        # Message statistics
        sessions_with_messages = await self.session_service.list(*base_query)
        total_messages = 0
        avg_messages_per_session = 0

        if sessions_with_messages:
            for session in sessions_with_messages:
                msg_count = await self.message_service.get_session_message_count(session.id)
                total_messages += msg_count

            avg_messages_per_session = total_messages / len(sessions_with_messages)

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": avg_messages_per_session,
            "sessions_with_conversations": len([s for s in sessions_with_messages if total_messages > 0])
        }
```

### Real-time Session Monitoring

```python
class SessionMonitoringService:
    """Real-time session monitoring and alerting."""

    def __init__(self):
        self.active_sessions: Dict[UUID, Dict[str, Any]] = {}
        self.message_buffers: Dict[UUID, List[Dict[str, Any]]] = {}

    async def track_session_activity(
        self,
        session_id: UUID,
        activity_type: str,
        metadata: Dict[str, Any] = None
    ):
        """Track session activity in real-time."""
        timestamp = datetime.utcnow()

        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "last_activity": timestamp,
                "message_count": 0,
                "activity_types": set()
            }

        session_data = self.active_sessions[session_id]
        session_data["last_activity"] = timestamp
        session_data["activity_types"].add(activity_type)

        if activity_type == "message":
            session_data["message_count"] += 1

        # Alert on unusual activity
        await self.check_session_alerts(session_id, session_data)

    async def check_session_alerts(self, session_id: UUID, session_data: Dict[str, Any]):
        """Check for session conditions that need alerting."""
        # High message rate alert
        if session_data["message_count"] > 100:
            await self.send_alert(
                "high_message_rate",
                f"Session {session_id} has {session_data['message_count']} messages"
            )

        # Long inactive period alert
        last_activity = session_data["last_activity"]
        if datetime.utcnow() - last_activity > timedelta(hours=2):
            await self.send_alert(
                "long_inactive_session",
                f"Session {session_id} inactive for over 2 hours"
            )
```

### Performance Metrics

```python
class SessionPerformanceTracker:
    """Tracks performance metrics for session operations."""

    def __init__(self):
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.error_rates: Dict[str, Dict[str, float]] = defaultdict(dict)

    @contextmanager
    def track_operation(self, operation_name: str):
        """Context manager for tracking operation performance."""
        start_time = time.time()
        error_occurred = False

        try:
            yield
        except Exception:
            error_occurred = True
            raise
        finally:
            duration = time.time() - start_time
            self.operation_times[operation_name].append(duration)

            # Update error rate
            total_ops = len(self.operation_times[operation_name])
            errors = self.error_rates[operation_name].get("errors", 0)
            if error_occurred:
                errors += 1

            self.error_rates[operation_name] = {
                "errors": errors,
                "error_rate": errors / total_ops,
                "avg_duration": sum(self.operation_times[operation_name]) / total_ops
            }
```

## 10. Session Backup and Recovery

### Session Data Export

```python
class SessionBackupService:
    """Service for session backup and export functionality."""

    async def export_session_data(
        self,
        session_id: UUID,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export complete session data including messages."""
        # Get session details
        session = await self.session_service.get(session_id)

        # Get all messages
        messages = await self.message_service.get_by_session(session_id)

        # Build export data structure
        export_data = {
            "session": {
                "id": str(session.id),
                "session_id": session.session_id,
                "session_name": session.session_name,
                "description": session.description,
                "is_active": session.is_active,
                "agent_name": session.agent_name,
                "agent_instructions": session.agent_instructions,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            },
            "messages": []
        }

        # Add messages with metadata
        for message in messages:
            message_data = {
                "id": str(message.id),
                "role": message.role.value,
                "content": message.content,
                "tool_call_id": message.tool_call_id,
                "tool_name": message.tool_name,
                "extra_data": json.loads(message.extra_data) if message.extra_data else None,
                "created_at": message.created_at.isoformat(),
                "updated_at": message.updated_at.isoformat()
            }
            export_data["messages"].append(message_data)

        if format == "json":
            return export_data
        elif format == "csv":
            return self.convert_to_csv(export_data)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def convert_to_csv(self, export_data: Dict[str, Any]) -> str:
        """Convert session data to CSV format."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "message_id", "role", "content", "tool_call_id",
            "tool_name", "created_at", "updated_at"
        ])

        # Write messages
        for message in export_data["messages"]:
            writer.writerow([
                message["id"],
                message["role"],
                message["content"],
                message["tool_call_id"],
                message["tool_name"],
                message["created_at"],
                message["updated_at"]
            ])

        return output.getvalue()
```

### Session Recovery

```python
class SessionRecoveryService:
    """Service for session recovery and restoration."""

    async def restore_session_from_backup(
        self,
        backup_data: Dict[str, Any],
        user_id: UUID
    ) -> AgentSessionSchema:
        """Restore session from backup data."""
        session_data = backup_data["session"]

        # Check for existing session with same ID
        existing_session = await self.session_service.get_by_session_id(
            session_data["session_id"],
            user_id
        )

        if existing_session:
            raise ValueError(f"Session {session_data['session_id']} already exists")

        # Create new session
        new_session_data = {
            "session_id": session_data["session_id"],
            "session_name": session_data["session_name"],
            "description": session_data["description"],
            "is_active": session_data["is_active"],
            "agent_name": session_data["agent_name"],
            "agent_instructions": session_data["agent_instructions"],
            "user_id": user_id
        }

        restored_session = await self.session_service.create(new_session_data)

        # Restore messages
        for message_data in backup_data["messages"]:
            message_data = {
                "session_id": restored_session.id,
                "role": MessageRole(message_data["role"]),
                "content": message_data["content"],
                "tool_call_id": message_data["tool_call_id"],
                "tool_name": message_data["tool_name"],
                "extra_data": json.dumps(message_data["extra_data"]) if message_data["extra_data"] else None,
            }
            await self.message_service.create(message_data)

        return self.session_service.to_schema(
            schema_type=AgentSessionSchema,
            data=restored_session
        )
```

### Automated Backup Strategy

```python
class AutomatedBackupManager:
    """Manages automated session backups."""

    def __init__(self):
        self.backup_interval = 86400  # Daily backups
        self.retention_period = 30  # Keep backups for 30 days

    async def schedule_daily_backups(self):
        """Schedule daily backup of all active sessions."""
        while True:
            try:
                await self.perform_daily_backups()
                await asyncio.sleep(self.backup_interval)
            except Exception as e:
                logger.error("Daily backup failed", error=str(e))
                await asyncio.sleep(3600)  # Retry in 1 hour

    async def perform_daily_backups(self):
        """Perform backup of all active sessions."""
        active_sessions = await self.session_service.list(
            m.AgentSession.is_active == True
        )

        backup_count = 0
        for session in active_sessions:
            try:
                backup_data = await self.backup_service.export_session_data(session.id)
                await self.store_backup(session.id, backup_data)
                backup_count += 1
            except Exception as e:
                logger.error(f"Backup failed for session {session.id}", error=str(e))

        logger.info("Daily backup completed", backup_count=backup_count)

    async def cleanup_old_backups(self):
        """Clean up backups older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_period)

        old_backups = await self.backup_storage.list_backups(
            created_before=cutoff_date
        )

        deleted_count = 0
        for backup in old_backups:
            await self.backup_storage.delete_backup(backup.id)
            deleted_count += 1

        logger.info("Backup cleanup completed", deleted_count=deleted_count)
```

## 11. Performance Optimization for Session Operations

### Database Optimization Strategies

#### Indexing Strategy

```sql
-- Session performance indexes
CREATE INDEX CONCURRENTLY ix_agent_session_user_active ON agent_session(user_id, is_active);
CREATE INDEX CONCURRENTLY ix_agent_session_created_at ON agent_session(created_at DESC);
CREATE INDEX CONCURRENTLY ix_agent_session_updated_at ON agent_session(updated_at DESC);

-- Message performance indexes
CREATE INDEX CONCURRENTLY ix_session_message_session_created ON session_message(session_id, created_at ASC);
CREATE INDEX CONCURRENTLY ix_session_message_session_role ON session_message(session_id, role);
```

#### Connection Pooling Configuration

```python
# Optimized database connection settings
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,  # Recycle connections every hour
    "pool_pre_ping": True,  # Validate connections before use
}
```

### Caching Strategy

```python
class SessionCacheManager:
    """Manages caching for session data to improve performance."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 hour
        self.message_cache_ttl = 1800  # 30 minutes

    async def cache_session(self, session: AgentSession):
        """Cache session data."""
        cache_key = f"session:{session.id}"
        session_data = {
            "id": str(session.id),
            "session_id": session.session_id,
            "user_id": str(session.user_id),
            "session_name": session.session_name,
            "is_active": session.is_active,
            "agent_name": session.agent_name,
            "agent_instructions": session.agent_instructions,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }

        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(session_data)
        )

    async def get_cached_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached session data."""
        cache_key = f"session:{session_id}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)
        return None

    async def cache_recent_messages(
        self,
        session_id: UUID,
        messages: List[SessionMessage]
    ):
        """Cache recent messages for quick access."""
        cache_key = f"session_messages:{session_id}"

        message_data = []
        for message in messages:
            message_data.append({
                "id": str(message.id),
                "role": message.role.value,
                "content": message.content,
                "created_at": message.created_at.isoformat()
            })

        await self.redis.setex(
            cache_key,
            self.message_cache_ttl,
            json.dumps(message_data)
        )

    async def invalidate_session_cache(self, session_id: UUID):
        """Invalidate session cache when data changes."""
        session_cache_key = f"session:{session_id}"
        messages_cache_key = f"session_messages:{session_id}"

        await self.redis.delete(session_cache_key, messages_cache_key)
```

### Async Operations and Concurrency

```python
class ConcurrentSessionManager:
    """Manages concurrent session operations efficiently."""

    def __init__(self):
        self.session_locks: Dict[UUID, asyncio.Lock] = {}
        self.lock_manager = asyncio.Lock()

    async def get_session_lock(self, session_id: UUID) -> asyncio.Lock:
        """Get or create a lock for session operations."""
        async with self.lock_manager:
            if session_id not in self.session_locks:
                self.session_locks[session_id] = asyncio.Lock()
            return self.session_locks[session_id]

    async def safe_message_creation(
        self,
        session_id: UUID,
        message_data: Dict[str, Any]
    ) -> SessionMessage:
        """Safely create message with session-level locking."""
        session_lock = await self.get_session_lock(session_id)

        async with session_lock:
            # Validate session state
            session = await self.session_service.get(session_id)
            if not session.is_active:
                raise ValueError("Cannot add messages to inactive session")

            # Create message
            message = await self.message_service.create(message_data)

            # Update session timestamp
            await self.session_service.update(
                session,
                updated_at=datetime.utcnow()
            )

            # Invalidate cache
            await self.cache_manager.invalidate_session_cache(session_id)

            return message

    async def batch_create_messages(
        self,
        session_id: UUID,
        messages_data: List[Dict[str, Any]]
    ) -> List[SessionMessage]:
        """Efficiently create multiple messages in a single transaction."""
        session_lock = await self.get_session_lock(session_id)

        async with session_lock:
            created_messages = []

            # Use database transaction for atomicity
            async with self.session_service.repository.session.begin():
                for message_data in messages_data:
                    message = await self.message_service.create(message_data)
                    created_messages.append(message)

                # Update session once at the end
                await self.session_service.update(
                    session_id,
                    updated_at=datetime.utcnow()
                )

            # Invalidate cache after batch creation
            await self.cache_manager.invalidate_session_cache(session_id)

            return created_messages
```

### Performance Monitoring and Metrics

```python
class SessionPerformanceMonitor:
    """Monitor and optimize session performance."""

    def __init__(self):
        self.operation_metrics: Dict[str, List[float]] = defaultdict(list)
        self.slow_query_threshold = 1.0  # seconds

    async def monitor_session_operation(
        self,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ):
        """Monitor session operation performance."""
        start_time = time.time()

        try:
            result = await operation_func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time

            # Record metric
            self.operation_metrics[operation_name].append(duration)

            # Alert on slow operations
            if duration > self.slow_query_threshold:
                logger.warning(
                    "Slow session operation detected",
                    operation=operation_name,
                    duration=duration,
                    threshold=self.slow_query_threshold
                )

            # Keep only recent metrics (last 1000 operations)
            if len(self.operation_metrics[operation_name]) > 1000:
                self.operation_metrics[operation_name] = self.operation_metrics[operation_name][-1000:]

    def get_performance_summary(self, operation_name: str) -> Dict[str, float]:
        """Get performance summary for an operation."""
        if operation_name not in self.operation_metrics:
            return {}

        durations = self.operation_metrics[operation_name]

        return {
            "count": len(durations),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p95_duration": sorted(durations)[int(len(durations) * 0.95)],
            "slow_operations": len([d for d in durations if d > self.slow_query_threshold])
        }
```

## 12. API Reference

### Session Endpoints

#### Core Session Operations

```http
# List Sessions
GET /api/agent-sessions
Authorization: Bearer <token>
Query Parameters:
- page: int (default: 1)
- size: int (default: 20)
- search: string (search in session_name)
- created_at: datetime range
- updated_at: datetime range

# Create Session
POST /api/agent-sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "session_user123_20241213_143000",
  "session_name": "Task Planning Discussion",
  "description": "Optional session description",
  "agent_name": "TodoAssistant",
  "agent_instructions": "Custom instructions for the agent",
  "is_active": true
}

# Get Session
GET /api/agent-sessions/{session_id}
Authorization: Bearer <token>

# Update Session
PATCH /api/agent-sessions/{session_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_name": "Updated Session Name",
  "description": "Updated description",
  "is_active": false
}

# Delete Session
DELETE /api/agent-sessions/{session_id}
Authorization: Bearer <token>
```

#### Session State Management

```http
# Activate Session
PUT /api/agent-sessions/{session_id}/activate
Authorization: Bearer <token>

# Deactivate Session
PUT /api/agent-sessions/{session_id}/deactivate
Authorization: Bearer <token>
```

#### Conversation Endpoint

```http
# Agent Conversation
POST /api/agent-sessions/conversation
Authorization: Bearer <token>
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Help me plan my tasks for tomorrow"
    }
  ],
  "session_id": "session_user123_20241213_143000",
  "session_name": "Task Planning Discussion"
}

Response:
{
  "session_id": "session_user123_20241213_143000",
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "response": "I'll help you plan your tasks for tomorrow...",
  "messages_count": 3,
  "session_active": true
}
```

### Message Endpoints

```http
# List Messages
GET /api/agent-sessions/{session_id}/messages
Authorization: Bearer <token>
Query Parameters:
- page: int (default: 1)
- size: int (default: 50)
- search: string (search in content)
- role: string (USER, ASSISTANT, SYSTEM, TOOL)
- created_at: datetime range

# Create Message
POST /api/agent-sessions/{session_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "user",
  "content": "Add task: Review project documentation",
  "tool_call_id": null,
  "tool_name": null,
  "extra_data": null
}

# Get Message
GET /api/agent-sessions/{session_id}/messages/{message_id}
Authorization: Bearer <token>

# Update Message
PATCH /api/agent-sessions/{session_id}/messages/{message_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Updated message content",
  "extra_data": "{\"key\": \"value\"}"
}

# Delete Message
DELETE /api/agent-sessions/{session_id}/messages/{message_id}
Authorization: Bearer <token>

# Clear All Messages
DELETE /api/agent-sessions/{session_id}/clear-messages
Authorization: Bearer <token>

Response:
{
  "deleted_count": 15
}
```

## 13. Best Practices and Guidelines

### Session Management Best Practices

1. **Session Lifecycle Management**
   - Always verify session ownership before operations
   - Implement proper session cleanup for inactive sessions
   - Use session states consistently across the application
   - Monitor session performance and resource usage

2. **Security Considerations**
   - Implement strict user isolation for sessions
   - Validate all input data for session and message creation
   - Use PII columns marking for sensitive data
   - Implement rate limiting for session operations

3. **Performance Optimization**
   - Use database indexes for frequently queried fields
   - Implement caching for active session data
   - Use batch operations for multiple message creation
   - Monitor slow queries and optimize database operations

4. **Error Handling**
   - Implement comprehensive error handling for all session operations
   - Provide meaningful error messages to clients
   - Use consistent error response formats
   - Log errors appropriately for debugging

5. **Testing Strategy**
   - Test session isolation and security thoroughly
   - Include performance testing for session operations
   - Test concurrent access scenarios
   - Validate cleanup and backup functionality

### Code Examples

#### Session Creation with Context Loading

```python
async def create_session_with_context(
    current_user: User,
    session_data: AgentSessionCreate,
    initial_context: Dict[str, Any] = None
) -> AgentSessionSchema:
    """Create session with initial context and memory."""
    # Create session
    session_dict = session_data.to_dict()
    session_dict["user_id"] = current_user.id

    session = await agent_session_service.create(session_dict)

    # Save initial context if provided
    if initial_context:
        await memory_manager.save_session_memory(
            session.id,
            initial_context
        )

    # Cache the new session
    await cache_manager.cache_session(session)

    return agent_session_service.to_schema(
        schema_type=AgentSessionSchema,
        data=session
    )
```

#### Efficient Message Retrieval with Caching

```python
async def get_session_messages_optimized(
    session_id: UUID,
    limit: int = 50,
    use_cache: bool = True
) -> List[SessionMessageSchema]:
    """Get session messages with caching optimization."""
    # Try cache first
    if use_cache:
        cached_messages = await cache_manager.get_cached_messages(session_id)
        if cached_messages and len(cached_messages) >= limit:
            return cached_messages[:limit]

    # Fallback to database
    messages = await message_service.get_recent_messages(session_id, limit)

    # Cache the results
    if use_cache and messages:
        await cache_manager.cache_recent_messages(session_id, messages)

    return [
        message_service.to_schema(
            schema_type=SessionMessageSchema,
            data=msg
        )
        for msg in messages
    ]
```

#### Session Health Monitoring

```python
async def monitor_session_health(session_id: UUID) -> Dict[str, Any]:
    """Monitor session health and provide recommendations."""
    session = await agent_session_service.get(session_id)
    message_count = await message_service.get_session_message_count(session_id)

    # Get recent activity
    recent_messages = await message_service.get_recent_messages(session_id, 5)
    last_activity = recent_messages[-1].created_at if recent_messages else session.updated_at

    # Health metrics
    hours_inactive = (datetime.utcnow() - last_activity).total_seconds() / 3600

    health_status = {
        "session_id": session_id,
        "is_active": session.is_active,
        "message_count": message_count,
        "hours_inactive": hours_inactive,
        "health_score": calculate_health_score(session, message_count, hours_inactive),
        "recommendations": generate_recommendations(session, message_count, hours_inactive)
    }

    return health_status

def calculate_health_score(session, message_count: int, hours_inactive: float) -> float:
    """Calculate session health score (0-100)."""
    score = 100.0

    # Deduct for inactivity
    if hours_inactive > 24:
        score -= min(30, hours_inactive / 24 * 10)
    elif hours_inactive > 1:
        score -= hours_inactive * 2

    # Deduct for low activity
    if message_count < 3:
        score -= 20
    elif message_count < 10:
        score -= 10

    # Deduct for inactive status
    if not session.is_active:
        score -= 25

    return max(0, score)

def generate_recommendations(session, message_count: int, hours_inactive: float) -> List[str]:
    """Generate health recommendations for session."""
    recommendations = []

    if hours_inactive > 24:
        recommendations.append("Consider deactivating or archiving this inactive session")

    if not session.is_active and hours_inactive < 1:
        recommendations.append("Consider reactivating this recently active session")

    if message_count < 3:
        recommendations.append("Session has minimal activity - consider engaging the agent")

    if session.agent_instructions and len(session.agent_instructions) > 10000:
        recommendations.append("Consider shortening agent instructions for better performance")

    return recommendations
```

This comprehensive documentation covers all aspects of agent session management in the todo application, from basic models to advanced optimization strategies and best practices. The system provides robust session handling with proper security, performance optimization, and monitoring capabilities.