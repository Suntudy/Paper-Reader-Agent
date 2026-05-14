"""Tool: fetch_arxiv — Download and parse a paper from arXiv."""

import re
import tempfile
import urllib.request
from pathlib import Path

from tools.registry import register
from tools.read_pdf import handler as read_pdf

DEFINITION = {
    "type": "function",
    "function": {
        "name": "fetch_arxiv",
        "description": "Download a paper from arXiv given its ID or URL. Returns the extracted text.",
        "parameters": {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "arXiv paper ID (e.g. '2310.06625') or full URL",
                }
            },
            "required": ["arxiv_id"],
        },
    },
}


def handler(arxiv_id: str) -> str:
    arxiv_id = arxiv_id.strip()
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", arxiv_id)
    if match:
        arxiv_id = match.group(1)
    else:
        return f"Error: Cannot parse arXiv ID from: {arxiv_id}"

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    try:
        tmp_path = Path(tempfile.gettempdir()) / f"arxiv_{arxiv_id}.pdf"
        if not tmp_path.exists():
            print(f"  Downloading {pdf_url} ...")
            req = urllib.request.Request(pdf_url, headers={"User-Agent": "PaperReaderAgent/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                tmp_path.write_bytes(resp.read())

        # Fetch abstract from API
        abs_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        abstract_info = ""
        try:
            req = urllib.request.Request(abs_url, headers={"User-Agent": "PaperReaderAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_text = resp.read().decode()
                title_match = re.search(r"<title>(.*?)</title>", xml_text, re.DOTALL)
                summary_match = re.search(r"<summary>(.*?)</summary>", xml_text, re.DOTALL)
                if title_match and summary_match:
                    abstract_info = (
                        f"Title: {title_match.group(1).strip()}\n"
                        f"Abstract: {summary_match.group(1).strip()}\n\n"
                    )
        except Exception:
            pass

        result = read_pdf(str(tmp_path))
        return abstract_info + result

    except Exception as e:
        return f"Error fetching arXiv paper: {e}"


register("fetch_arxiv", DEFINITION, handler)
