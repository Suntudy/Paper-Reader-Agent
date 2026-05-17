"""
MCP Client — sync bridge for Paper Reader Agent.

Manages MCP server subprocesses and provides sync API for the agent loop.
Uses a background asyncio event loop in a daemon thread to keep MCP
connections alive across multiple tool calls.
"""

import asyncio
import json
import threading
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_DIR = Path(__file__).parent.parent
CONFIG_PATH = Path(__file__).parent / "config.json"

# ── Module state ──

_loop = None
_thread = None
_servers = {}
_tool_routing = {}


# ── Background event loop ──

def _ensure_loop():
    global _loop, _thread
    if _loop is not None and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()
    _thread = threading.Thread(target=_loop.run_forever, daemon=True, name="mcp-loop")
    _thread.start()


def _run_sync(coro, timeout=30):
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=timeout)


# ── Server connection ──

class _ServerConnection:
    """Manages one MCP server subprocess + session as a long-lived asyncio task."""

    def __init__(self, name, command, args):
        self.name = name
        self.command = command
        self.args = args
        self.session = None
        self.tools = []
        self._ready = asyncio.Event()
        self._shutdown = asyncio.Event()
        self._task = None

    async def start(self):
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            cwd=str(PROJECT_DIR),
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.session = session
                    result = await session.list_tools()
                    self.tools = result.tools if hasattr(result, "tools") else []
                    self._ready.set()
                    await self._shutdown.wait()
        except Exception as e:
            print(f"  MCP server '{self.name}' error: {e}", flush=True)
            self._ready.set()
        finally:
            self.session = None

    async def call_tool(self, tool_name, arguments):
        if not self.session:
            return json.dumps({"error": f"Server '{self.name}' not connected"})
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            parts = []
            for block in (result.content or []):
                if hasattr(block, "text"):
                    parts.append(block.text)
            return "\n".join(parts) if parts else ""
        except Exception as e:
            return json.dumps({"error": f"MCP tool call failed: {e}"})

    def request_shutdown(self):
        if _loop and _loop.is_running():
            _loop.call_soon_threadsafe(self._shutdown.set)


# ── Schema conversion ──

def _mcp_to_openai(server_name, mcp_tool):
    """Convert MCP tool schema to OpenAI function-calling format."""
    safe_server = server_name.replace("-", "_")
    tool_name = f"mcp_{safe_server}_{mcp_tool.name}"

    input_schema = dict(mcp_tool.inputSchema) if mcp_tool.inputSchema else {}
    if "type" not in input_schema:
        input_schema["type"] = "object"
    if "properties" not in input_schema:
        input_schema["properties"] = {}

    return tool_name, {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": mcp_tool.description or mcp_tool.name,
            "parameters": input_schema,
        },
    }


# ── Public sync API ──

def init_mcp_servers():
    """Start all MCP servers from config. Returns list of OpenAI tool definitions."""
    if not CONFIG_PATH.exists():
        return []

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    servers_config = config.get("servers", {})
    if not servers_config:
        return []

    _ensure_loop()
    tool_definitions = []

    for name, cfg in servers_config.items():
        command = cfg["command"]
        args = cfg.get("args", [])

        conn = _ServerConnection(name, command, args)
        conn._task = asyncio.run_coroutine_threadsafe(conn.start(), _loop)

        try:
            _run_sync(conn._ready.wait(), timeout=60)
        except Exception as e:
            print(f"  MCP server '{name}' failed to start: {e}", flush=True)
            continue

        if not conn.tools:
            print(f"  MCP server '{name}' connected but has no tools", flush=True)
            continue

        _servers[name] = conn

        for mcp_tool in conn.tools:
            prefixed_name, definition = _mcp_to_openai(name, mcp_tool)
            _tool_routing[prefixed_name] = (name, mcp_tool.name)
            tool_definitions.append(definition)

    return tool_definitions


def call_mcp_tool(tool_name, arguments):
    """Call an MCP tool by its prefixed name. Returns result string."""
    routing = _tool_routing.get(tool_name)
    if not routing:
        return json.dumps({"error": f"Unknown MCP tool: {tool_name}"})

    server_name, original_name = routing
    conn = _servers.get(server_name)
    if not conn:
        return json.dumps({"error": f"MCP server '{server_name}' not connected"})

    return _run_sync(conn.call_tool(original_name, arguments))


def get_mcp_tool_names():
    """Return set of all MCP tool names (prefixed) for routing checks."""
    return set(_tool_routing.keys())


def shutdown_mcp_servers():
    """Gracefully shut down all MCP servers."""
    for conn in _servers.values():
        conn.request_shutdown()

    for conn in _servers.values():
        if conn._task:
            try:
                conn._task.result(timeout=5)
            except Exception:
                pass

    _servers.clear()
    _tool_routing.clear()

    global _loop, _thread
    if _loop and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)
    if _thread:
        _thread.join(timeout=3)
    _loop = None
    _thread = None
