"""Tool: run_python — Execute Python code in a subprocess."""

import subprocess
import tempfile
from pathlib import Path

from tools.common import OUTPUT_DIR
from tools.registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": "Execute Python code and return stdout/stderr. Use for data processing, model implementation, and visualization.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                }
            },
            "required": ["code"],
        },
    },
}


def handler(code: str) -> str:
    tmp = Path(tempfile.gettempdir()) / "agent_run.py"
    tmp.write_text(code, encoding="utf-8")

    try:
        result = subprocess.run(
            ["python", str(tmp)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(OUTPUT_DIR),
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if not output.strip():
            output = "(No output)"
        if len(output) > 20000:
            output = output[:20000] + "\n[... truncated ...]"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (120s limit)"
    except Exception as e:
        return f"Error executing code: {e}"


register("run_python", DEFINITION, handler)
