"""Tool: write_file — Write content to the output directory."""

import re
from tools.common import OUTPUT_DIR
from tools.registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file in the output directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename (will be saved in output/ directory)",
                },
                "content": {
                    "type": "string",
                    "description": "File content to write",
                },
            },
            "required": ["filename", "content"],
        },
    },
}


def handler(filename: str, content: str) -> str:
    filename = re.sub(r'[<>:"|?*]', "_", filename)
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Written to {path}"


register("write_file", DEFINITION, handler)
