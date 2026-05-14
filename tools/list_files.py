"""Tool: list_files — List files in a directory."""

from pathlib import Path
from tools.registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files in a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list",
                }
            },
            "required": ["directory"],
        },
    },
}


def handler(directory: str) -> str:
    path = Path(directory).expanduser()
    if not path.exists():
        return f"Error: Directory not found: {path}"
    if not path.is_dir():
        return f"Error: Not a directory: {path}"

    entries = []
    for item in sorted(path.iterdir()):
        prefix = "[DIR] " if item.is_dir() else "      "
        entries.append(f"{prefix}{item.name}")
    return "\n".join(entries) if entries else "(empty directory)"


register("list_files", DEFINITION, handler)
