#!/usr/bin/env python3
"""
Example Skill for Oracle Agent 5.0

This skill demonstrates best practices for creating custom tools.
It provides utility functions for date/time operations and text processing.
"""

import datetime
import json
import re
from typing import Any, Dict

# ============================================================================
# Skill Metadata
# ============================================================================

SKILL_NAME = "example_skill"
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = "Example skill demonstrating Oracle 5.0 capabilities"

# ============================================================================
# Lifecycle Hooks
# ============================================================================


def setup():
    """
    Called when the skill is loaded.

    Use this for initialization like:
    - Loading configuration
    - Establishing connections
    - Initializing caches
    """
    print(f"[{SKILL_NAME}] Skill initialized")
    # You could load config from a file here
    # Or set up a database connection


def teardown():
    """
    Called when Oracle shuts down or skills are reloaded.

    Use this for cleanup like:
    - Closing connections
    - Saving state
    - Releasing resources
    """
    print(f"[{SKILL_NAME}] Skill shutting down")


# ============================================================================
# Tool Handlers
# ============================================================================


def get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
    """
    Get the current date and time.

    Args:
        timezone: Timezone name (e.g., "UTC", "US/Eastern", "Europe/London")

    Returns:
        Dict with current time information
    """
    try:
        # Note: Full timezone support would require pytz
        # This is a simplified version
        now = datetime.datetime.now()

        return {
            "success": True,
            "result": {
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timezone": timezone,
                "day_of_week": now.strftime("%A"),
                "week_of_year": int(now.strftime("%W")),
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to get time: {str(e)}"}


def calculate_duration(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Calculate duration between two dates.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Dict with duration information
    """
    try:
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")

        delta = end - start

        return {
            "success": True,
            "result": {
                "days": delta.days,
                "hours": delta.days * 24,
                "weeks": delta.days // 7,
                "business_days": sum(
                    1 for i in range(delta.days + 1) if (start + datetime.timedelta(days=i)).weekday() < 5
                ),
            },
        }
    except ValueError as e:
        return {"success": False, "error": f"Invalid date format. Use YYYY-MM-DD: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_text(text: str, format_type: str = "uppercase") -> Dict[str, Any]:
    """
    Format text in various ways.

    Args:
        text: Input text to format
        format_type: Type of formatting (uppercase, lowercase, title, snake_case, camelCase)

    Returns:
        Dict with formatted text
    """
    try:
        if format_type == "uppercase":
            result = text.upper()
        elif format_type == "lowercase":
            result = text.lower()
        elif format_type == "title":
            result = text.title()
        elif format_type == "snake_case":
            # Convert to snake_case
            result = re.sub(r"[^\w\s]", "", text)
            result = re.sub(r"\s+", "_", result).lower()
        elif format_type == "camelCase":
            # Convert to camelCase
            words = re.split(r"[^\w]+", text)
            result = words[0].lower() + "".join(word.capitalize() for word in words[1:])
        else:
            return {"success": False, "error": f"Unknown format_type: {format_type}"}

        return {"success": True, "result": {"original": text, "formatted": result, "format_type": format_type}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_json(json_string: str, extract_path: str = None) -> Dict[str, Any]:
    """
    Parse and extract data from JSON.

    Args:
        json_string: JSON string to parse
        extract_path: Optional dot-notation path to extract (e.g., "data.items.0.name")

    Returns:
        Dict with parsed data
    """
    try:
        data = json.loads(json_string)

        # Extract nested value if path specified
        if extract_path:
            keys = extract_path.split(".")
            for key in keys:
                if isinstance(data, dict):
                    if key not in data:
                        return {"success": False, "error": f"Path not found: {extract_path}"}
                    data = data[key]
                elif isinstance(data, list):
                    try:
                        idx = int(key)
                        if idx >= len(data):
                            return {"success": False, "error": f"Index out of range: {idx}"}
                        data = data[idx]
                    except ValueError:
                        return {"success": False, "error": f"Invalid array index: {key}"}
                else:
                    return {"success": False, "error": f"Cannot traverse path at: {key}"}

        return {"success": True, "result": data}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Tool Definitions
# ============================================================================

TOOLS = [
    {
        "name": "get_current_time",
        "description": (
            "Get the current date and time. Returns ISO format datetime, date, "
            "time, day of week, and week of year."
        ),
        "parameters": {
            "timezone": {
                "type": "string",
                "description": "Timezone name (e.g., 'UTC', 'US/Eastern', 'Europe/London'). Defaults to UTC.",
                "default": "UTC",
            }
        },
        "handler": get_current_time,
    },
    {
        "name": "calculate_duration",
        "description": "Calculate the duration between two dates. Returns days, hours, weeks, and business days.",
        "parameters": {
            "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
            "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
        },
        "handler": calculate_duration,
    },
    {
        "name": "format_text",
        "description": "Format text in various ways: uppercase, lowercase, title case, snake_case, or camelCase.",
        "parameters": {
            "text": {"type": "string", "description": "Input text to format"},
            "format_type": {
                "type": "string",
                "description": "Formatting type: 'uppercase', 'lowercase', 'title', 'snake_case', 'camelCase'",
                "enum": ["uppercase", "lowercase", "title", "snake_case", "camelCase"],
                "default": "uppercase",
            },
        },
        "handler": format_text,
    },
    {
        "name": "parse_json",
        "description": "Parse a JSON string and optionally extract a nested value using dot notation path.",
        "parameters": {
            "json_string": {"type": "string", "description": "JSON string to parse"},
            "extract_path": {
                "type": "string",
                "description": "Optional dot-notation path to extract (e.g., 'data.items.0.name')",
                "default": None,
            },
        },
        "handler": parse_json,
    },
]

# ============================================================================
# Usage Examples
# ============================================================================

"""
Example conversations with Oracle using this skill:

User: "What time is it?"
Oracle: [calls get_current_time]
→ Result: "It's currently 14:30:22 UTC on Monday, March 15, 2026"

User: "Format this in snake_case: Hello World"
Oracle: [calls format_text with text="Hello World", format_type="snake_case"]
→ Result: "hello_world"

User: "How many days between 2026-01-01 and 2026-12-31?"
Oracle: [calls calculate_duration]
→ Result: "There are 365 days between those dates (261 business days)"

User: "Extract the name from this JSON: {'user': {'name': 'Alice', 'age': 30}}"
Oracle: [calls parse_json with extract_path="user.name"]
→ Result: "Alice"
"""
