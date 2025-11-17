# Importance Levels & Scheduling

This document provides a comprehensive guide to the importance level system and scheduling features in the Todo Domain. The application implements a sophisticated time management system with conflict detection, priority-based sorting, and intelligent scheduling algorithms.

## Table of Contents

1. [Importance Enumeration](#importance-enumeration)
2. [Scheduling System Architecture](#scheduling-system-architecture)
3. [Plan Time Attributes & Validation](#plan-time-attributes--validation)
4. [Time Conflict Detection Algorithms](#time-conflict-detection-algorithms)
5. [Priority-Based Sorting & Filtering](#priority-based-sorting--filtering)
6. [Scheduling Constraints & Business Rules](#scheduling-constraints--business-rules)
7. [Time Zone Handling](#time-zone-handling)
8. [Schedule Visualization & Analysis](#schedule-visualization--analysis)
9. [Batch Scheduling Operations](#batch-scheduling-operations)
10. [Performance Optimization](#performance-optimization)

## Importance Enumeration

### Definition

The importance system uses a four-level enumeration to classify todo items by priority and urgency:

```python
class Importance(enum.Enum):
    """Importance levels for todo items."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

### Level Definitions

| Level | Value | Description | Use Case |
|-------|-------|-------------|----------|
| **NONE** | `"none"` | Default importance level | Tasks without specific priority |
| **LOW** | `"low"` | Low priority tasks | Optional activities, nice-to-have items |
| **MEDIUM** | `"medium"` | Moderate priority | Important but not urgent tasks |
| **HIGH** | `"high"` | High priority | Critical or time-sensitive tasks |

### Importance in Scheduling

Importance levels influence:
- **Scheduling Priority**: High importance tasks get preferred time slots
- **Conflict Resolution**: Higher importance may override lower priority conflicts
- **Schedule Analysis**: Importance weighting in schedule recommendations
- **Filtering**: Filter todos by importance level for focused views

```python
# Example: Setting importance in todo creation
importance_enum = Importance(parsed.importance.lower())  # Convert string to enum

# Database schema
importance: Mapped[Importance] = mapped_column(
    Enum(Importance, name="importance_enum", native_enum=False),
    nullable=False,
    default=Importance.NONE
)
```

## Scheduling System Architecture

### Core Components

The scheduling system consists of:

1. **Time Fields**: `start_time`, `end_time`, `alarm_time`
2. **Conflict Detection**: Overlap detection algorithms
3. **Time Slot Management**: Available slot finding
4. **Intelligent Scheduling**: AI-powered time recommendations

### Time Field Relationships

```python
class Todo(UUIDAuditBase):
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=False)
    alarm_time: Mapped[datetime | None] = mapped_column(nullable=True)
```

- **start_time**: Beginning of the scheduled time slot
- **end_time**: End of the scheduled time slot
- **alarm_time**: Optional reminder/notification time

### Scheduling Workflow

1. **Time Validation**: Ensure start_time < end_time
2. **Conflict Detection**: Check for overlapping existing todos
3. **Time Zone Conversion**: Handle user's local time zones
4. **Slot Allocation**: Find optimal time slots if auto-scheduling
5. **Persistence**: Store validated schedule in database

## Plan Time Attributes & Validation

### Time Field Validation

All time-related fields undergo comprehensive validation:

```python
async def _validate_time_updates(
    update_data: dict,
    todo,
    user_tz: ZoneInfo,
    todo_service,
    current_user_id: UUID
) -> str | None:
    """Validate time ordering and check for conflicts."""

    # Validate ordering
    if "start_time" in update_data and "end_time" in update_data:
        if update_data["end_time"] <= update_data["start_time"]:
            return "Error: End time must be after start time"

    # Check for conflicts
    if "start_time" in update_data or "end_time" in update_data:
        final_start = update_data.get("start_time", todo.start_time)
        final_end = update_data.get("end_time", todo.end_time)

        if isinstance(final_start, datetime) and isinstance(final_end, datetime):
            conflicts = await todo_service.check_time_conflict(
                current_user_id, final_start, final_end, todo.id
            )
            if conflicts:
                return _format_conflict_message(conflicts, user_tz)

    return None
```

### Time Parsing with Time Zones

The system supports multiple datetime formats with time zone handling:

```python
def _parse_datetime_with_timezone(date_str: str, user_tz: ZoneInfo) -> datetime | None:
    """Parse datetime string with timezone support."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=user_tz).astimezone(UTC)
        except ValueError:
            continue
    return None
```

**Supported Formats:**
- `"YYYY-MM-DD HH:MM:SS"` - Full datetime with time
- `"YYYY-MM-DD"` - Date only (defaults to midnight)

**Time Zone Support:**
- Automatic conversion to UTC for storage
- Local time display using user's timezone
- Support for IANA timezone names (e.g., "America/New_York", "Asia/Shanghai")

## Time Conflict Detection Algorithms

### Overlap Detection Logic

The system uses interval overlap detection:

```python
async def check_time_conflict(
    self,
    user_id: UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_todo_id: UUID | None = None
) -> list[m.Todo]:
    """Check for time conflicts with existing todos for a user."""

    # Two time ranges overlap if:
    # 1. The new start_time is before existing end_time AND
    # 2. The new end_time is after existing start_time
    filters = [
        m.Todo.user_id == user_id,
        m.Todo.start_time < end_time,  # existing start is before new end
        m.Todo.end_time > start_time,  # existing end is after new start
    ]

    # Exclude the current todo if updating
    if exclude_todo_id:
        filters.append(m.Todo.id != exclude_todo_id)

    conflicts, _ = await self.list_and_count(*filters)
    return list(conflicts)
```

### Conflict Resolution Strategies

1. **Prevention**: Block creation of conflicting todos
2. **Notification**: Provide detailed conflict information
3. **Rescheduling**: Suggest alternative time slots
4. **Priority Override**: Allow high-importance tasks to override (future feature)

### Conflict Message Formatting

```python
def _format_conflict_message(conflicts: list[m.Todo], user_tz: ZoneInfo) -> str:
    """Format conflict details for user display."""
    details = [
        f"• '{c.item}' ({c.start_time.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')} - {c.end_time.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')})"
        for c in conflicts
    ]
    return (
        "❌ Time conflict detected! The requested time slot conflicts with existing todos:\n"
        + "\n".join(details)
        + "\n\nPlease choose a different time or use the schedule_todo tool to find an available slot."
    )
```

## Priority-Based Sorting & Filtering

### Database-Level Filtering

The system supports filtering by multiple criteria:

```python
# Controller-level filtering
@get(path="/", operation_id="list_todos")
async def list_todos(
    self,
    current_user: m.User,
    todo_service: TodoService,
    filters: Annotated[list[FilterTypes], Dependency(skip_validation=True)],
    start_time_from: Annotated[datetime | None, Parameter(...)] = None,
    start_time_to: Annotated[datetime | None, Parameter(...)] = None,
    end_time_from: Annotated[datetime | None, Parameter(...)] = None,
    end_time_to: Annotated[datetime | None, Parameter(...)] = None,
) -> OffsetPagination[TodoModel]:
    """List all todo items with optional time filtering."""
    user_filter = m.Todo.user_id == current_user.id
    additional_filters = []

    # Add custom datetime filters
    if start_time_from:
        additional_filters.append(m.Todo.start_time >= start_time_from)
    if start_time_to:
        additional_filters.append(m.Todo.start_time <= start_time_to)
    if end_time_from:
        additional_filters.append(m.Todo.end_time >= end_time_from)
    if end_time_to:
        additional_filters.append(m.Todo.end_time <= end_time_to)

    all_filters = [user_filter] + additional_filters + list(filters)
    results, total = await todo_service.list_and_count(*all_filters)
    return todo_service.to_schema(data=results, total=total, schema_type=TodoModel)
```

### Importance-Based Filtering

```python
# In agent implementations
if parsed.importance:
    try:
        filters.append(m.Todo.importance == Importance(parsed.importance.lower()))
    except ValueError:
        return f"Error: Invalid importance level '{parsed.importance}'. Use: none, low, medium, high"
```

### Sorting Strategies

1. **Chronological**: Sort by start_time for schedule views
2. **Importance-Weighted**: High importance tasks first
3. **Deadline-Based**: Sort by alarm_time for approaching tasks
4. **Creation Order**: Sort by created_time for recent items

## Scheduling Constraints & Business Rules

### Core Constraints

1. **Time Ordering**: `start_time < end_time` (strictly required)
2. **User Isolation**: Users only see/manage their own todos
3. **Conflict Prevention**: No overlapping time slots allowed
4. **Time Zone Consistency**: All times stored in UTC, displayed in user timezone

### Business Rules

#### 1. Working Hours Constraints
```python
def _find_free_time_slots(day_todos: list, current_date: datetime, user_tz: ZoneInfo) -> list[str]:
    """Find free time slots in a day with working hours."""
    work_start = current_date.replace(hour=8, minute=0)  # 8 AM
    work_end = current_date.replace(hour=22, minute=0)   # 10 PM

    # Only consider slots within working hours
    # Minimum slot duration: 30 minutes
```

#### 2. Duration Requirements
- **Minimum Duration**: 30 minutes for meaningful scheduling
- **Default Duration**: 60 minutes if not specified
- **Maximum Duration**: No hard limit, but practical constraints apply

#### 3. Preferred Time-of-Day Support
```python
def _find_optimal_time_slot(target_date: datetime, parsed: ScheduleTodoArgs, existing: list, user_tz: ZoneInfo) -> datetime | None:
    """Find the optimal time slot based on user preferences."""
    prefs = {
        "morning": (8, 12),    # 8 AM - 12 PM
        "afternoon": (12, 17), # 12 PM - 5 PM
        "evening": (17, 21)    # 5 PM - 9 PM
    }

    # Try preferred time of day first
    if parsed.preferred_time_of_day and parsed.preferred_time_of_day.lower() in prefs:
        start_hour, end_hour = prefs[parsed.preferred_time_of_day.lower()]
        slot = _find_free_slot(target_date, start_hour, end_hour, parsed.duration_minutes, existing, user_tz)
        if slot:
            return slot

    # Fall back to any available time slot
    for period in ["morning", "afternoon", "evening"]:
        start_hour, end_hour = prefs[period]
        slot = _find_free_slot(target_date, start_hour, end_hour, parsed.duration_minutes, existing, user_tz)
        if slot:
            return slot

    return None
```

## Time Zone Handling & Considerations

### Time Zone Architecture

The application implements robust time zone support:

1. **Storage**: All datetime values stored in UTC
2. **Display**: Converted to user's local timezone for presentation
3. **Parsing**: Accept timezone-aware input from users
4. **Validation**: Ensure timezone validity and consistency

### Time Zone Conversion Patterns

```python
# Storage: Always convert to UTC
def convert_to_utc(user_datetime: datetime, user_tz: ZoneInfo) -> datetime:
    """Convert user's local datetime to UTC for storage."""
    return user_datetime.replace(tzinfo=user_tz).astimezone(UTC)

# Display: Convert from UTC to user timezone
def convert_to_local_time(utc_datetime: datetime, user_tz: ZoneInfo) -> datetime:
    """Convert UTC datetime to user's local timezone for display."""
    return utc_datetime.astimezone(user_tz)

# Parsing with timezone
def _parse_timezone_and_date(timezone_str: str | None, target_date_str: str | None) -> tuple[ZoneInfo, datetime]:
    """Parse timezone and target date from input arguments."""
    user_tz = ZoneInfo("UTC")  # Default to UTC
    if timezone_str:
        try:
            user_tz = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError as e:
            msg = f"Invalid timezone '{timezone_str}'"
            raise ValueError(msg) from e

    # Parse target date with timezone
    if target_date_str:
        start_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=user_tz)
    else:
        start_date = datetime.now(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)

    return user_tz, start_date
```

### Time Zone Best Practices

1. **Default Handling**: Default to UTC when timezone not specified
2. **Validation**: Validate timezone names against IANA database
3. **Consistency**: Maintain consistent timezone throughout request lifecycle
4. **User Preference**: Store user's preferred timezone in profile (future feature)

### Supported Time Zone Formats

- **IANA Names**: `"America/New_York"`, `"Europe/London"`, `"Asia/Shanghai"`
- **UTC Offset**: `"UTC+5:30"`, `"UTC-8:00"` (via ZoneInfo conversion)
- **Common Names**: `"EST"`, `"PST"` (discouraged, use full IANA names)

## Schedule Visualization & Analysis

### Schedule Analysis Features

The system provides comprehensive schedule analysis capabilities:

```python
async def analyze_schedule_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the analyze_schedule function."""
    # Parse user request
    parsed = AnalyzeScheduleArgs.model_validate_json(args)

    # Get timezone and target date
    user_tz, start_date = _parse_timezone_and_date(parsed.timezone, parsed.target_date)

    # Retrieve todos for date range
    todos = await _get_todos_for_date_range(start_date, parsed.include_days, todo_service, current_user_id)

    # Generate day-by-day analysis
    analysis = _analyze_schedule_by_days(todos, start_date, parsed.include_days, user_tz)

    return f"📊 Schedule Analysis ({parsed.include_days} days starting from {start_date.strftime('%Y-%m-%d')}):\n\n" + "\n\n".join(analysis)
```

### Daily Schedule Analysis

```python
def _analyze_single_day(todos: Sequence[Todo], current_date: datetime, user_tz: ZoneInfo) -> str:
    """Analyze a single day's schedule."""
    day_start = current_date.replace(hour=0, minute=0, second=0)
    day_end = current_date.replace(hour=23, minute=59, second=59)
    day_start_utc = day_start.astimezone(UTC)
    day_end_utc = day_end.astimezone(UTC)

    # Filter todos for this day
    day_todos = [
        t for t in todos
        if t.alarm_time is not None and day_start_utc <= t.alarm_time <= day_end_utc
    ]

    # Sort by time
    day_todos.sort(key=lambda x: x.alarm_time or datetime.min.replace(tzinfo=UTC))

    # Find available time slots
    free_slots = _find_free_time_slots(day_todos, current_date, user_tz)

    # Format analysis
    day_str = current_date.strftime("%A, %B %d, %Y")
    result = f"📅 {day_str}:\n"

    if day_todos:
        result += "  Scheduled todos:\n"
        for t in day_todos:
            if t.alarm_time:
                local_time = t.alarm_time.astimezone(user_tz)
                result += f"    • {local_time.strftime('%H:%M')} - {t.item} (importance: {t.importance.value})\n"
    else:
        result += "  No scheduled todos\n"

    if free_slots:
        result += "  Available time slots:\n" + "\n".join(free_slots)
    else:
        result += "  ⚠️  No significant free time slots available"

    return result
```

### Free Time Slot Detection

```python
def _find_free_time_slots(day_todos: list, current_date: datetime, user_tz: ZoneInfo) -> list[str]:
    """Find free time slots in a day."""
    work_start = current_date.replace(hour=8, minute=0)  # 8 AM
    work_end = current_date.replace(hour=22, minute=0)   # 10 PM

    if not day_todos:
        return [f"  🟢 {work_start.strftime('%H:%M')} - {work_end.strftime('%H:%M')} (14 hours available)"]

    free = []
    current_time = work_start

    for todo in day_todos:
        if todo.alarm_time is not None:
            todo_time_local = todo.alarm_time.astimezone(user_tz)
            if current_time < todo_time_local:
                gap_hours = (todo_time_local - current_time).total_seconds() / 3600
                if gap_hours >= 0.5:  # Minimum 30 minutes
                    free.append(
                        f"  🟢 {current_time.strftime('%H:%M')} - {todo_time_local.strftime('%H:%M')} ({gap_hours:.1f} hours available)"
                    )
            # Assume 1 hour duration for each todo
            current_time = max(current_time, todo_time_local + timedelta(hours=1))

    # Check remaining time
    if current_time < work_end:
        gap_hours = (work_end - current_time).total_seconds() / 3600
        if gap_hours >= 0.5:
            free.append(
                f"  🟢 {current_time.strftime('%H:%M')} - {work_end.strftime('%H:%M')} ({gap_hours:.1f} hours available)"
            )

    return free
```

## Batch Scheduling Operations

### Batch Update System

The application supports batch scheduling operations for efficient management:

```python
async def batch_update_schedule_impl(ctx: RunContextWrapper, args: str) -> str:
    """Implementation of the batch_update_schedule function."""
    parsed = BatchUpdateScheduleArgs.model_validate_json(args)

    # Preview mode without confirmation
    if not parsed.confirm:
        return _generate_update_preview(parsed)

    user_tz = _get_user_timezone(parsed.timezone)
    if isinstance(user_tz, str):
        return user_tz  # Error message

    # Apply updates
    success, failed = await _apply_schedule_updates(parsed.updates, user_tz, todo_service, current_user_id)
    return _format_update_results(success, failed)
```

### Update Preview System

```python
def _generate_update_preview(parsed: BatchUpdateScheduleArgs) -> str:
    """Generate a preview of proposed schedule changes."""
    preview = "📋 Proposed Schedule Changes:\n\n"
    for i, upd in enumerate(parsed.updates, 1):
        preview += f"{i}. Todo ID ending in ...{upd.todo_id[-8:]}:\n   New time: {upd.new_time}\n   Reason: {upd.reason}\n\n"
    preview += "⚠️  To confirm these changes, set 'confirm: true' in your request."
    return preview
```

### Batch Update Application

```python
async def _apply_schedule_updates(updates: list, user_tz: ZoneInfo, todo_service, current_user_id: UUID) -> tuple[list[str], list[str]]:
    """Apply the schedule updates and return results."""
    success, failed = [], []

    for upd in updates:
        try:
            todo_uuid = UUID(upd.todo_id)
            todo = await todo_service.get_todo_by_id(todo_uuid, current_user_id)

            if not todo:
                failed.append(f"Todo {upd.todo_id} not found")
                continue

            # Parse and validate new time
            new_time_obj = datetime.strptime(upd.new_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=user_tz)

            # Apply update
            todo.alarm_time = new_time_obj.astimezone(UTC)
            await todo_service.update(todo)
            success.append(f"✅ '{todo.item}' rescheduled to {upd.new_time}")

        except ValueError:
            failed.append(f"Invalid time format for todo {upd.todo_id}: {upd.new_time}")
        except Exception as e:
            failed.append(f"Error updating todo {upd.todo_id}: {e!s}")

    return success, failed
```

## Performance Optimization

### Database Query Optimization

#### 1. Efficient Conflict Detection

```python
# Optimized conflict checking using database-level filters
async def check_time_conflict(self, user_id: UUID, start_time: datetime, end_time: datetime, exclude_todo_id: UUID | None = None) -> list[m.Todo]:
    """Optimized time conflict detection using database queries."""

    # Use indexed columns for efficient filtering
    filters = [
        m.Todo.user_id == user_id,           # User isolation
        m.Todo.start_time < end_time,        # Overlap condition 1
        m.Todo.end_time > start_time,        # Overlap condition 2
    ]

    # Exclude current todo during updates
    if exclude_todo_id:
        filters.append(m.Todo.id != exclude_todo_id)

    # Efficient query with limit to prevent excessive results
    conflicts, _ = await self.list_and_count(*filters, LimitOffset(limit=50))
    return list(conflicts)
```

#### 2. Time-Range Filtering

```python
# Date range filtering using database indexes
async def _get_todos_for_date_range(start_date: datetime, include_days: int, todo_service, current_user_id: UUID) -> Sequence[Todo]:
    """Get todos for the specified date range efficiently."""
    end_date = start_date + timedelta(days=include_days)
    start_utc = start_date.astimezone(UTC)
    end_utc = end_date.astimezone(UTC)

    # Use indexed datetime columns for efficient filtering
    filters = [
        m.Todo.user_id == current_user_id,
        m.Todo.alarm_time >= start_utc,
        m.Todo.alarm_time <= end_utc
    ]

    # Limit results for performance
    todos, _ = await todo_service.list_and_count(*filters, LimitOffset(limit=100, offset=0))
    return todos
```

#### 3. Index Strategy

Recommended database indexes for scheduling performance:

```sql
-- User-specific time-based queries
CREATE INDEX idx_todo_user_start_time ON todo(user_id, start_time);
CREATE INDEX idx_todo_user_end_time ON todo(user_id, end_time);
CREATE INDEX idx_todo_user_alarm_time ON todo(user_id, alarm_time);

-- Conflict detection queries
CREATE INDEX idx_todo_user_time_range ON todo(user_id, start_time, end_time);

-- Importance-based filtering
CREATE INDEX idx_todo_user_importance ON todo(user_id, importance);
```

### Caching Strategies

#### 1. Schedule Analysis Caching

```python
# Cache schedule analysis results to avoid repeated calculations
from functools import lru_cache
from datetime import date

@lru_cache(maxsize=128)
def get_day_analysis_cache_key(user_id: UUID, analysis_date: date, include_days: int) -> str:
    """Generate cache key for schedule analysis."""
    return f"schedule_analysis:{user_id}:{analysis_date.isoformat()}:{include_days}"
```

#### 2. Conflict Detection Optimization

```python
# Cache recent conflict checks for performance
class ConflictCache:
    def __init__(self, ttl_minutes: int = 5):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get_conflicts(self, user_id: UUID, start_time: datetime, end_time: datetime) -> list[m.Todo] | None:
        """Get cached conflicts if available and not expired."""
        key = (user_id, start_time, end_time)
        if key in self.cache:
            cached_time, conflicts = self.cache[key]
            if datetime.now(UTC) - cached_time < self.ttl:
                return conflicts
        return None

    def set_conflicts(self, user_id: UUID, start_time: datetime, end_time: datetime, conflicts: list[m.Todo]) -> None:
        """Cache conflict detection results."""
        key = (user_id, start_time, end_time)
        self.cache[key] = (datetime.now(UTC), conflicts)
```

### Memory Optimization

#### 1. Efficient Data Loading

```python
# Use selectin loading for optimal memory usage
class TodoService(SQLAlchemyAsyncRepositoryService[m.Todo]):
    class Repository(SQLAlchemyAsyncRepository[m.Todo]):
        """Todo SQLAlchemy Repository with optimized loading."""

        model_type = m.Todo

        async def get_todos_with_tags(self, user_id: UUID, limit: int = 50) -> list[m.Todo]:
            """Get todos with efficiently loaded tags."""
            return await self.list(
                m.Todo.user_id == user_id,
                load=[("todo_tags", "tag")],  # Eager load tags with join
                LimitOffset(limit=limit)
            )
```

#### 2. Pagination for Large Datasets

```python
# Always paginate large result sets
async def get_paginated_schedule(
    self,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
    date_filter: datetime | None = None
) -> OffsetPagination[TodoModel]:
    """Get paginated schedule with optional date filtering."""
    filters = [m.Todo.user_id == user_id]

    if date_filter:
        filters.append(m.Todo.start_time >= date_filter)

    return await self.list_and_count(
        *filters,
        LimitOffset(limit=page_size, offset=(page - 1) * page_size)
    )
```

### Query Performance Monitoring

```python
# Performance monitoring for scheduling queries
import time
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')

class PerformanceMonitor(Protocol[T]):
    async def execute(self, operation: str, query_func: callable) -> T:
        """Execute query with performance monitoring."""

async def monitor_query_performance(operation: str, query_func: callable) -> any:
    """Monitor and log query performance."""
    start_time = time.time()
    try:
        result = await query_func()
        duration = time.time() - start_time

        # Log performance metrics
        if duration > 1.0:  # Log slow queries
            logger.warning(f"Slow query detected: {operation} took {duration:.2f}s")
        else:
            logger.debug(f"Query performance: {operation} took {duration:.3f}s")

        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Query failed: {operation} after {duration:.3f}s - {e}")
        raise
```

## Advanced Usage Examples

### Smart Scheduling with Preferences

```python
# Example: Schedule a meeting with preferred time and importance
schedule_args = ScheduleTodoArgs(
    item="Team Standup Meeting",
    description="Daily sync with development team",
    target_date="2025-01-15",
    duration_minutes=30,
    importance="high",
    timezone="America/New_York",
    preferred_time_of_day="morning",  # 8-12 AM preferred
    tags=["work", "meetings"]
)

# This will find the best available slot in the morning, or any slot if morning is full
```

### Conflict-Aware Todo Creation

```python
# Example: Create todo with automatic conflict detection
create_args = CreateTodoArgs(
    item="Client Presentation",
    start_time="2025-01-15 14:00:00",
    end_time="2025-01-15 16:00:00",
    importance="high",
    timezone="America/New_York"
)

# System will:
# 1. Parse times with timezone conversion
# 2. Validate time ordering
# 3. Check for conflicts with existing todos
# 4. Return success or detailed conflict information
```

### Schedule Analysis for Planning

```python
# Example: Analyze upcoming week for planning
analysis_args = AnalyzeScheduleArgs(
    target_date="2025-01-15",  # Monday
    timezone="America/New_York",
    include_days=7  # Full week
)

# Returns detailed analysis including:
# - Daily todo breakdown by importance
# - Available time slots
# - Schedule density warnings
# - Recommendations for rescheduling
```

This comprehensive documentation covers all aspects of the importance levels and scheduling system, providing developers with the knowledge needed to effectively use and extend these features.