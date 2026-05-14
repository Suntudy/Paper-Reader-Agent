"""
Tool package — auto-discovers all tools via self-registration.

Each tool file calls registry.register() at import time.
This __init__.py auto-scans all .py files in the tools/ directory,
so adding a new tool only requires creating a new file.
"""

import importlib
import pkgutil
from pathlib import Path

# Auto-import all .py files in this package (except __init__, registry, common)
_SKIP = {"__init__", "registry", "common"}
_package_dir = Path(__file__).parent

for module_info in pkgutil.iter_modules([str(_package_dir)]):
    if module_info.name not in _SKIP:
        importlib.import_module(f"tools.{module_info.name}")

# Public API (used by agent.py)
from tools.registry import get_all_definitions, get_all_handlers, execute_tool

TOOL_DEFINITIONS = get_all_definitions()
TOOL_HANDLERS = get_all_handlers()
