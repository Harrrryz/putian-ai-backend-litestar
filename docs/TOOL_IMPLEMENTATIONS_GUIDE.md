# Todo Agent Tools Implementation Guide

## Overview

The `tool_implementations.py` module contains the core implementation functions for the AI todo agent's tools. These functions enable the agent to perform comprehensive todo management operations including CRUD operations, intelligent scheduling, conflict detection, and batch updates.

## Tool Architecture

```
Todo Agent Tools Hierarchy
│
├── 🗂️ CRUD Operations
│   ├── create_todo_impl()          # Create new todos with conflict detection
│   ├── update_todo_impl()          # Update existing todos with validation
│   ├── delete_todo_impl()          # Delete todos safely
│   └── get_todo_list_impl()        # Retrieve filtered todo lists
│
├── 📅 Schedule Management  
│   ├── schedule_todo_impl()        # Smart scheduling with time slot finding
│   ├── analyze_schedule_impl()     # Multi-day schedule analysis
│   └── batch_update_schedule_impl() # Bulk schedule modifications
│
└── 🔧 Helper Functions
    ├── Time & Date Parsing
    │   ├── _parse_datetime_with_timezone()
    │   ├── _parse_timezone_and_date()
    │   └── _determine_schedule_target_date()
    │
    ├── Validation & Conflict Detection
    │   ├── _validate_time_updates()
    │   ├── _find_free_slot()
    │   └── _detect_scheduling_conflicts()
    │
    ├── Schedule Analysis
    │   ├── _analyze_schedule_by_days()
    │   ├── _analyze_single_day()
    │   └── _find_free_time_slots()
    │
    └── Formatting & Results
        ├── _format_todo_results()
        ├── _format_scheduling_success()
        └── _format_update_results()
```

## Tool Functions

### 1. CRUD Operations

#### `create_todo_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Creates new todo items with comprehensive validation and conflict detection.

**Features**:
- ✅ Timezone-aware datetime parsing
- ✅ Time conflict detection with existing todos
- ✅ Importance level validation
- ✅ Start/end time ordering validation
- ✅ Optional alarm time setting

**Input Format**:
```json
{
  "item": "Task name",
  "description": "Task description", 
  "importance": "high|medium|low|none",
  "start_time": "YYYY-MM-DD HH:MM:SS",
  "end_time": "YYYY-MM-DD HH:MM:SS",
  "alarm_time": "YYYY-MM-DD HH:MM:SS", // optional
  "timezone": "America/New_York",
  "tags": ["tag1", "tag2"] // optional
}
```

**Example Output**:
```
Successfully created todo 'Team Meeting' (ID: 123e4567-e89b-12d3-a456-426614174000) 
scheduled from 2025-08-24 14:00 to 2025-08-24 15:30 (tags: work, meeting)
```

#### `update_todo_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Updates existing todos with field-level modifications and conflict checking.

**Features**:
- ✅ Partial updates (only specified fields)
- ✅ Time conflict detection for schedule changes
- ✅ Field validation and type conversion
- ✅ Ownership verification

**Input Format**:
```json
{
  "todo_id": "uuid-string",
  "item": "New task name", // optional
  "description": "New description", // optional
  "importance": "high", // optional
  "start_time": "YYYY-MM-DD HH:MM:SS", // optional
  "end_time": "YYYY-MM-DD HH:MM:SS", // optional
  "alarm_time": "YYYY-MM-DD HH:MM:SS", // optional
  "timezone": "America/New_York"
}
```

#### `delete_todo_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Safely deletes todo items with ownership verification.

**Features**:
- ✅ UUID validation
- ✅ Existence checking
- ✅ User ownership verification
- ✅ Confirmation messages

**Input Format**:
```json
{
  "todo_id": "uuid-string"
}
```

#### `get_todo_list_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Retrieves filtered lists of todos with pagination and timezone support.

**Features**:
- ✅ Date range filtering
- ✅ Importance level filtering
- ✅ Timezone-aware display
- ✅ Pagination support
- ✅ Rich formatting

**Input Format**:
```json
{
  "from_date": "YYYY-MM-DD", // optional
  "to_date": "YYYY-MM-DD", // optional
  "importance": "high|medium|low|none", // optional
  "timezone": "America/New_York", // optional
  "limit": 20 // optional, default varies
}
```

### 2. Schedule Management

#### `schedule_todo_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Intelligently schedules todos by finding optimal time slots.

**Features**:
- 🧠 Smart time slot detection
- ⏰ Preferred time-of-day scheduling (morning/afternoon/evening)
- 🔍 Conflict avoidance
- 📊 Duration-based slot finding
- 🌍 Timezone support

**Input Format**:
```json
{
  "item": "Task name",
  "description": "Task description",
  "importance": "medium",
  "duration_minutes": 90,
  "preferred_time_of_day": "morning|afternoon|evening", // optional
  "target_date": "YYYY-MM-DD", // optional, defaults to today/tomorrow
  "timezone": "America/New_York" // optional
}
```

**Algorithm**:
1. Parse target date and timezone
2. Retrieve existing todos for the day
3. Try preferred time slots first
4. Fall back to any available slots
5. Create todo if slot found, otherwise suggest alternatives

#### `analyze_schedule_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Provides comprehensive multi-day schedule analysis with availability detection.

**Features**:
- 📊 Multi-day schedule overview
- 🕐 Free time slot identification
- 📈 Daily workload analysis
- 🌍 Timezone-aware display
- ⏱️ Gap analysis between todos

**Input Format**:
```json
{
  "target_date": "YYYY-MM-DD", // optional, defaults to today
  "include_days": 7, // number of days to analyze
  "timezone": "America/New_York" // optional
}
```

**Example Output**:
```
📊 Schedule Analysis (7 days starting from 2025-08-24):

📅 Sunday, August 24, 2025:
  Scheduled todos:
    • 09:00 - Team standup (importance: high)
    • 14:00 - Client meeting (importance: medium)
  Available time slots:
    🟢 10:00 - 14:00 (4.0 hours available)
    🟢 15:30 - 22:00 (6.5 hours available)
```

#### `batch_update_schedule_impl(ctx: RunContextWrapper, args: str) -> str`

**Purpose**: Performs bulk schedule modifications with preview and confirmation.

**Features**:
- 📋 Preview mode for safety
- ✅ Confirmation requirement
- 🔄 Batch processing
- 📊 Success/failure reporting
- 🕐 Timezone handling

**Input Format**:
```json
{
  "updates": [
    {
      "todo_id": "uuid-string",
      "new_time": "YYYY-MM-DD HH:MM:SS",
      "reason": "Conflict resolution"
    }
  ],
  "confirm": false, // set to true to execute
  "timezone": "America/New_York"
}
```

## Helper Functions Documentation

### Time & Date Processing

#### `_parse_datetime_with_timezone(date_str: str, user_tz: ZoneInfo) -> datetime | None`
- Parses date strings in multiple formats (`YYYY-MM-DD HH:MM:SS`, `YYYY-MM-DD`)
- Applies timezone information and converts to UTC
- Returns `None` for invalid formats

#### `_determine_schedule_target_date(timezone_str, target_date_str) -> tuple[ZoneInfo, datetime]`
- Smart date selection: defaults to tomorrow if after 6 PM, otherwise today
- Handles timezone parsing with proper error handling
- Returns both timezone and target date objects

### Validation & Conflict Detection

#### `_validate_time_updates(update_data: dict, todo, user_tz: ZoneInfo, todo_service, current_user_id: UUID) -> str | None`
- Validates time ordering (end > start)
- Checks for scheduling conflicts with other todos
- Returns error message if validation fails, `None` if valid

#### `_find_free_slot(target_date, start_hour, end_hour, duration_minutes, existing, user_tz) -> datetime | None`
- Searches for available time slots within specified hours
- Considers existing todo durations and gaps
- Returns optimal start time or `None` if no slot available

### Schedule Analysis

#### `_analyze_single_day(todos: Sequence[Todo], current_date: datetime, user_tz: ZoneInfo) -> str`
- Analyzes a single day's schedule
- Identifies gaps between scheduled items
- Calculates available time slots (minimum 30 minutes)
- Formats results with emoji indicators

#### `_find_free_time_slots(day_todos: list, current_date: datetime, user_tz: ZoneInfo) -> list[str]`
- Identifies free time within work hours (8 AM - 10 PM)
- Calculates gap durations between scheduled todos
- Filters out slots shorter than 30 minutes
- Returns formatted time slot descriptions

## Data Flow

```
User Request → Agent → Tool Implementation → Service Layer → Database
                ↓
            Validation & Processing
                ↓  
            Conflict Detection
                ↓
            Timezone Conversion
                ↓
            Result Formatting → Response
```

## Error Handling

The implementation includes comprehensive error handling:

- **Input Validation**: JSON parsing, UUID validation, date format checking
- **Business Logic**: Time conflicts, ownership verification, ordering constraints  
- **Service Errors**: Database connection issues, constraint violations
- **User-Friendly Messages**: Clear error descriptions with suggested fixes

## Timezone Support

All functions support timezone-aware operations:
- Accepts timezone strings (e.g., "America/New_York", "Asia/Shanghai")
- Converts user times to UTC for storage
- Displays results in user's timezone
- Handles timezone parsing errors gracefully

## Integration Points

The tools integrate with:
- **Todo Service**: CRUD operations, conflict checking
- **Tag Service**: Tag management (future enhancement)
- **User Context**: Authentication and ownership
- **Database Models**: Todo, User, Tag entities

## Usage Patterns

### Creating a Todo with Smart Scheduling
```python
# Agent receives: "Schedule a 2-hour client meeting tomorrow morning"
# 1. Calls schedule_todo_impl with parsed parameters
# 2. Function finds optimal morning slot
# 3. Creates todo with conflict checking
# 4. Returns formatted confirmation
```

### Analyzing Weekly Schedule
```python
# Agent receives: "Show my schedule for the next week"
# 1. Calls analyze_schedule_impl with 7-day range
# 2. Function retrieves todos for date range
# 3. Analyzes each day individually
# 4. Returns comprehensive schedule overview
```

This implementation provides a robust foundation for AI-powered todo management with intelligent scheduling capabilities and comprehensive error handling.
