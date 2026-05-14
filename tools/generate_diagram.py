"""Tool: generate_diagram — Generate a Mermaid diagram and save as Markdown."""

import re
from tools.common import OUTPUT_DIR
from tools.registry import register

DIAGRAMS_DIR = OUTPUT_DIR / "diagrams"
DIAGRAMS_DIR.mkdir(exist_ok=True)

DEFINITION = {
    "type": "function",
    "function": {
        "name": "generate_diagram",
        "description": (
            "Generate a Mermaid diagram (flowchart, sequence, class, etc.) "
            "and save it as a Markdown file. Use this to visualize model architectures, "
            "data pipelines, or paper workflows. The output .md file can be previewed "
            "directly in VSCode with a Mermaid extension."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Diagram title, also used as the filename (e.g. 'PatchTST_architecture')",
                },
                "mermaid_code": {
                    "type": "string",
                    "description": "Mermaid diagram code (e.g. 'graph TD\\n  A-->B')",
                },
                "description": {
                    "type": "string",
                    "description": "Optional brief description of what the diagram shows",
                },
            },
            "required": ["title", "mermaid_code"],
        },
    },
}


def handler(title: str, mermaid_code: str, description: str = "") -> str:
    safe_name = re.sub(r'[<>:"|?*\s]+', "_", title).strip("_")
    filename = f"{safe_name}.md"
    path = DIAGRAMS_DIR / filename

    lines = [f"# {title}", ""]
    if description:
        lines += [description, ""]
    lines += ["```mermaid", mermaid_code, "```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return f"Diagram saved to {path}\nPreview it in VSCode with a Mermaid preview extension."


register("generate_diagram", DEFINITION, handler)
