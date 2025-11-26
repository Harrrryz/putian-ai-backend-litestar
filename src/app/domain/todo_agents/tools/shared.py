"""Shared utility functions for todo agent tools."""

from __future__ import annotations

import json

def preprocess_args(args: str) -> str:
    """Preprocess tool arguments to handle double-encoded JSON arrays.

    Some LLMs may send array fields as stringified JSON within the JSON string,
    e.g., tags: '["study"]' instead of tags: ["study"].
    This function parses the JSON and re-serializes it to ensure proper structure.

    Args:
        args: JSON string containing tool arguments

    Returns:
        Preprocessed JSON string with proper array encoding
    """
    try:
        data = json.loads(args)

        # Check if any field is a string that looks like a JSON array
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
                try:
                    # Try to parse it as JSON
                    parsed_array = json.loads(value)
                    if isinstance(parsed_array, list):
                        data[key] = parsed_array
                except (json.JSONDecodeError, ValueError):
                    # If it fails to parse, leave it as is
                    pass

        return json.dumps(data)
    except (json.JSONDecodeError, ValueError):
        # If we can't parse the args, return them as-is
        return args
