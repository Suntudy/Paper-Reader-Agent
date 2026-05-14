"""Tool registry — tools call register() to add themselves."""

_registry = {}


def register(name: str, schema: dict, handler):
    """Register a tool. Called by each tool file at import time."""
    _registry[name] = {"schema": schema, "handler": handler}


def get_all_definitions() -> list:
    """Return all tool schemas (for passing to LLM API)."""
    return [entry["schema"] for entry in _registry.values()]


def get_all_handlers() -> dict:
    """Return {name: handler} mapping."""
    return {name: entry["handler"] for name, entry in _registry.items()}


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name."""
    entry = _registry.get(name)
    if not entry:
        return f"Error: Unknown tool '{name}'"
    try:
        return entry["handler"](**arguments)
    except TypeError as e:
        return f"Error: Invalid arguments for {name}: {e}"
