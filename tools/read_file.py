"""Tool: read_file — Read a text file."""

from pathlib import Path
from tools.registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file and return its content.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                }
            },
            "required": ["file_path"],
        },
    },
}


def handler(file_path: str) -> str:
    path = Path(file_path).expanduser()
    if not path.exists():
        return f"Error: File not found: {path}"
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > 50000:
            content = content[:50000] + "\n[... truncated ...]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


register("read_file", DEFINITION, handler)
