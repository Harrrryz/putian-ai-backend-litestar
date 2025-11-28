# Fix for SSE Agent Streaming Error - Double-Encoded JSON Arrays

## Problem

The agent streaming was failing with the following error:

```
Agent streaming failed: Error running tool create_todo: 1 validation error for CreateTodoArgs
tags
  Input should be a valid array [type=list_type, input_value='["study"]', input_type=str]
```

The issue was that the LLM was sending array fields (like `tags`) as stringified JSON within the JSON string, causing double encoding:
- **Expected**: `{"tags": ["study"]}`
- **Received**: `{"tags": "[\"study\"]"}`

## Root Cause

When the OpenAI/GLM agent returns tool arguments, some LLMs may serialize array fields as JSON strings instead of native arrays. This happens because:

1. The agent serializes the tool arguments to JSON
2. Some LLMs may pre-serialize certain fields (arrays) before the outer serialization
3. This results in double-encoded JSON where arrays become strings containing JSON

## Solution

Added a preprocessing step (`_preprocess_args` function) that:

1. Parses the incoming JSON string
2. Detects fields that are strings starting with `[` and ending with `]`
3. Attempts to parse these strings as JSON arrays
4. Replaces the double-encoded strings with properly parsed arrays
5. Re-serializes the corrected data structure

### Code Changes

**File**: `src/app/domain/todo_agents/tools/todo_crud_tools.py`

1. **Added imports**: Added `json` to the imports at the top of the file

2. **Added `_preprocess_args` function**:
```python
def _preprocess_args(args: str) -> str:
    """Preprocess tool arguments to handle double-encoded JSON arrays."""
    try:
        data = json.loads(args)
        
        # Check if any field is a string that looks like a JSON array
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
                try:
                    parsed_array = json.loads(value)
                    if isinstance(parsed_array, list):
                        data[key] = parsed_array
                except (json.JSONDecodeError, ValueError):
                    pass
        
        return json.dumps(data)
    except (json.JSONDecodeError, ValueError):
        return args
```

3. **Updated tool implementations**:
   - `create_todo_impl`: Added `args = _preprocess_args(args)` before parsing
   - `schedule_todo_impl`: The scheduling module imports `_preprocess_args` and applies it before parsing

These are the two functions that accept `tags` parameters which could be double-encoded.

## Testing

Verified the fix handles:
- ✅ Double-encoded arrays: `'["study"]'` → `["study"]`
- ✅ Properly encoded arrays: `["study"]` → `["study"]` (unchanged)
- ✅ Multiple double-encoded arrays in the same object
- ✅ Missing array fields (no error)
- ✅ Invalid JSON strings (gracefully handled)

## Impact

- **Fixes**: The validation error when creating todos with tags via the agent
- **Backwards Compatible**: Does not affect properly formatted input
- **Robust**: Handles edge cases gracefully without breaking
- **Minimal**: Only affects the two functions that accept array parameters

## Future Considerations

If additional tool functions accept array parameters, they should also use `_preprocess_args()` before parsing arguments.
