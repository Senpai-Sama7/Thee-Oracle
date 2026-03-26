# Oracle Skills

This directory contains custom skills that extend Oracle Agent's capabilities.

## What is a Skill?

A skill is a Python module that provides one or more tools (functions) that Oracle can call. Skills enable you to:

- Add custom integrations with external APIs
- Create domain-specific tools
- Share reusable functionality across projects
- Extend Oracle without modifying core code

## Quick Start

1. Create a new Python file in this directory (e.g., `my_skill.py`)
2. Define your skill metadata and tools
3. Restart Oracle or call `oracle skills reload`

## Skill Structure

```python
# my_skill.py

# Skill metadata
SKILL_NAME = "my_skill"

# Tool definitions
TOOLS = [
    {
        "name": "my_tool",
        "description": "What this tool does",
        "parameters": {
            "param1": {
                "type": "string",
                "description": "Description of param1"
            },
            "param2": {
                "type": "integer",
                "description": "Description of param2"
            }
        },
        "handler": my_tool_handler
    }
]

# Optional: Setup function called when skill loads
def setup():
    """Initialize the skill."""
    print(f"{SKILL_NAME} initialized")

# Optional: Teardown function called when skill unloads
def teardown():
    """Clean up resources."""
    print(f"{SKILL_NAME} shutting down")

# Tool handler function
def my_tool_handler(param1: str, param2: int) -> dict:
    """
    Implement your tool logic here.
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Dict with 'success' key and result/error
    """
    try:
        # Your tool logic here
        result = f"Processed {param1} with {param2}"
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

## Tool Definition Format

Each tool in the `TOOLS` list must have:

- `name`: Unique tool name (within the skill)
- `description`: What the tool does (shown to the AI)
- `parameters`: JSON Schema-like parameter definitions
- `handler`: Callable that implements the tool

### Parameter Types

Supported parameter types:

- `string`: Text values
- `integer`: Whole numbers
- `number`: Decimal numbers
- `boolean`: true/false
- `array`: Lists of values
- `object`: Nested dictionaries

### Handler Function

The handler can be:

- A regular function: `def handler(args): ...`
- An async function: `async def handler(args): ...`
- A lambda: `lambda x: {"success": True, "result": x}`

The handler must return a dict with at minimum:

```python
{"success": True, "result": ...}
# or
{"success": False, "error": "..."}
```

## Lifecycle Hooks

### setup()

Called when the skill is loaded. Use for:

- Initializing connections
- Loading configuration
- Setting up caches

Can be sync or async:

```python
def setup():
    pass

# or

async def setup():
    await initialize_connection()
```

### teardown()

Called when Oracle shuts down or skills are reloaded. Use for:

- Closing connections
- Saving state
- Cleaning up resources

Can be sync or async:

```python
def teardown():
    pass

# or

async def teardown():
    await close_connection()
```

## Examples

See `example_skill.py` for a complete working example.

## Best Practices

1. **Descriptive Names**: Use clear, descriptive tool names
2. **Good Descriptions**: Help the AI understand when to use your tool
3. **Error Handling**: Always return `{"success": False, "error": ...}` on failure
4. **Type Safety**: Validate input types before processing
5. **Idempotency**: Tools should be safe to call multiple times
6. **Timeouts**: Keep operations reasonably fast (< 30 seconds)
7. **Logging**: Use `print()` or `logging` for debugging

## Troubleshooting

### Skill not loading

- Check that the file has a `.py` extension
- Verify the `TOOLS` attribute exists and is a list
- Check Oracle logs for import errors

### Tool not found

- Check that the tool name is unique
- If it conflicts with a built-in tool, it will be prefixed: `skillname__toolname`
- Reload skills after making changes

### Handler errors

- Ensure the handler is callable
- Verify the handler signature matches parameters
- Check return value has `success` key

## Security

Skills run with the same permissions as Oracle Agent:

- Filesystem access is sandboxed to the workspace
- Network access depends on Oracle's security mode
- Be cautious with user input
- Don't hardcode secrets (use environment variables)

## Sharing Skills

To share a skill:

1. Copy the skill file to another Oracle installation's `skills/` directory
2. Or publish to the Oracle Skill Registry (coming soon)
3. Include a README explaining dependencies and setup

## Advanced Topics

### Using External Libraries

Skills can import external libraries if they're installed in Oracle's environment:

```python
import requests

TOOLS = [
    {
        "name": "fetch_weather",
        "description": "Get weather data",
        "parameters": {...},
        "handler": lambda city: requests.get(f"https://api.weather.com/{city}").json()
    }
]
```

### Stateful Skills

Skills can maintain state between calls:

```python
# State at module level
cache = {}

def my_handler(query: str) -> dict:
    if query in cache:
        return {"success": True, "result": cache[query]}
    
    result = expensive_operation(query)
    cache[query] = result
    return {"success": True, "result": result}
```

### Async Skills

For I/O-bound operations, use async handlers:

```python
import aiohttp

async def fetch_handler(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return {"success": True, "result": await response.text()}
```

## Support

For questions or issues with skills:

- Check the example skill: `example_skill.py`
- Review Oracle documentation
- Open an issue on GitHub
