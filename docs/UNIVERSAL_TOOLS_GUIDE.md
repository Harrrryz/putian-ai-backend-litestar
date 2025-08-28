# Universal Tools Documentation

## Overview

The `universal_tools.py` module contains tools that can be used by any AI agent across the system. These tools provide common functionality that multiple agents may need, reducing code duplication and ensuring consistency.

## Available Tools

### `get_user_datetime`

**Purpose**: Get the user's current date, time, and timezone information.

This tool is essential when any language model needs to know the current time context for scheduling, filtering, or any time-based operations. It provides comprehensive datetime information including timezone awareness, business day context, and formatted output.

**Function**: `get_user_datetime_impl(ctx: RunContextWrapper, args: str) -> str`

**Parameters**:
```json
{
  "timezone": "America/New_York"  // optional, defaults to UTC
}
```

**Example Usage**:

```python
# In an AI agent tool implementation
from app.domain.todo_agents.tools.universal_tools import get_user_datetime_impl

# Get current time in UTC (default)
result = get_user_datetime_impl(ctx, "{}")

# Get current time in specific timezone
args = json.dumps({"timezone": "America/New_York"})
result = get_user_datetime_impl(ctx, args)
```

**Example Output**:
```
🕐 Current date and time: Wednesday, August 28, 2025 at 10:30:45 AM EDT
🌍 Timezone: America/New_York (UTC-4)
📅 ISO format: 2025-08-28T10:30:45-04:00
📆 Day of week: Wednesday
📊 Week number: 35
⏰ Time period: 🌅 Morning
💼 Business day: Yes (weekday)
```

**Features**:
- ✅ Timezone validation and support for all standard timezone identifiers
- ✅ Comprehensive time information (day of week, week number, time period)
- ✅ Business day detection (weekday vs weekend)
- ✅ Multiple time formats (human-readable and ISO format)
- ✅ UTC offset calculation and display
- ✅ Error handling for invalid timezones
- ✅ Emoji indicators for better visual formatting

**Supported Timezones**:
- UTC (default)
- America/New_York, America/Los_Angeles, America/Chicago, etc.
- Europe/London, Europe/Paris, Europe/Berlin, etc.  
- Asia/Tokyo, Asia/Shanghai, Asia/Kolkata, etc.
- All standard IANA timezone identifiers

## When to Use Universal Tools

### For Todo Agents
- **Scheduling Operations**: When creating or updating todos, use `get_user_datetime` to understand the current context
- **Date Filtering**: When filtering todos by date ranges, get the user's current date/time for relative operations
- **Time-based Validation**: When validating if a scheduled time makes sense (e.g., not in the past)

### For Other Agents
- **Time-sensitive Operations**: Any operation that needs to know "now" in the user's context
- **Logging and Audit**: When recording when actions were performed
- **Deadline Calculations**: When computing time-based deadlines or reminders
- **Schedule Coordination**: When coordinating between different time zones

## Integration with Agent System

### Tool Registration

The universal tools are registered in the `UNIVERSAL_TOOLS` dictionary:

```python
UNIVERSAL_TOOLS = {
    "get_user_datetime": {
        "function": get_user_datetime_impl,
        "description": "Get the user's current date, time, and timezone information",
        "parameters": {
            "type": "object", 
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The user's timezone (e.g., 'America/New_York', 'Europe/London'). Defaults to UTC if not specified."
                }
            },
            "required": []
        }
    }
}
```

### Adding New Universal Tools

To add new universal tools:

1. **Create the Implementation Function**:
   ```python
   def new_tool_impl(ctx: RunContextWrapper, args: str) -> str:
       """Implementation of the new universal tool."""
       # Tool implementation here
       pass
   ```

2. **Add Helper Functions** (if needed):
   ```python
   def _helper_function(param: str) -> str:
       """Private helper function for the tool."""
       pass
   ```

3. **Register the Tool**:
   ```python
   UNIVERSAL_TOOLS["new_tool"] = {
       "function": new_tool_impl,
       "description": "Description of what the tool does",
       "parameters": {
           # JSON schema for parameters
       }
   }
   ```

4. **Update Documentation**: Add the new tool to this documentation file.

## Best Practices

### Error Handling
- Always validate input parameters and provide clear error messages
- Use specific exception types instead of generic `Exception`
- Return user-friendly error messages with emoji indicators (❌)

### Parameter Handling
- Support optional parameters with sensible defaults
- Validate parameters and provide helpful error messages
- Use JSON for structured input parameters

### Output Formatting
- Use emojis and formatting for better readability
- Provide comprehensive information without being overwhelming
- Include context that helps users understand the results

### Code Organization
- Break complex functions into smaller helper functions
- Use type hints for better code maintainability
- Follow the project's coding standards and linting rules

## Testing

The `test_universal_tools.py` file provides examples of how to test the universal tools:

```python
# Run the test file
python src/app/domain/todo_agents/tools/test_universal_tools.py
```

This will demonstrate all the different use cases and show the expected output formats.

## Future Enhancements

Potential universal tools that could be added:

1. **User Preference Tools**: Get user's preferred date/time formats, timezone settings
2. **Validation Tools**: Validate emails, phone numbers, URLs
3. **Formatting Tools**: Format currencies, numbers, dates consistently
4. **Calculation Tools**: Time duration calculations, date arithmetic
5. **Conversion Tools**: Unit conversions, timezone conversions
6. **Utility Tools**: Generate UUIDs, create temporary identifiers

These tools should follow the same patterns and conventions established by the datetime tool.
