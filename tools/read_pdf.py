"""Tool: read_pdf — Extract text from a local PDF file."""

from pathlib import Path
from tools.registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_pdf",
        "description": "Read a PDF file and extract its text content. Use for local paper PDFs.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the PDF file",
                }
            },
            "required": ["file_path"],
        },
    },
}


def handler(file_path: str) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "Error: PyMuPDF not installed. Run: pip install PyMuPDF"

    path = Path(file_path).expanduser()
    if not path.exists():
        return f"Error: File not found: {path}"

    try:
        doc = fitz.open(str(path))
        text_parts = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{text}")
        doc.close()

        full_text = "\n".join(text_parts)
        if len(full_text) > 80000:
            full_text = full_text[:80000] + "\n\n[... truncated, paper too long ...]"
        return full_text
    except Exception as e:
        return f"Error reading PDF: {e}"


register("read_pdf", DEFINITION, handler)
