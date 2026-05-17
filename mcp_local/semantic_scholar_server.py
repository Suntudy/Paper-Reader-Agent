"""MCP Server: Semantic Scholar — Academic paper search via S2 API."""

import json
import time
import urllib.request
import urllib.parse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "semantic-scholar",
    instructions="Search and retrieve academic paper metadata from Semantic Scholar.",
)

_API_BASE = "https://api.semanticscholar.org/graph/v1"
_LAST_REQUEST_TIME = 0.0


def _api_get(url: str) -> dict:
    """Make a rate-limited GET request to Semantic Scholar API."""
    global _LAST_REQUEST_TIME
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _LAST_REQUEST_TIME = time.time()

    req = urllib.request.Request(url, headers={"User-Agent": "PaperReaderAgent/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


@mcp.tool()
def search_papers(query: str, limit: int = 5) -> str:
    """Search for academic papers by keyword.

    Args:
        query: Search query (e.g. 'time series foundation model')
        limit: Number of results to return (default 5, max 20)
    """
    limit = min(limit, 20)
    encoded = urllib.parse.quote(query)
    fields = "title,authors,year,abstract,citationCount,externalIds,openAccessPdf"
    url = f"{_API_BASE}/paper/search?query={encoded}&limit={limit}&fields={fields}"

    try:
        data = _api_get(url)
    except Exception as e:
        return json.dumps({"error": f"Semantic Scholar API error: {e}"})

    papers = []
    for p in data.get("data", []):
        arxiv_id = (p.get("externalIds") or {}).get("ArXiv", "")
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3])
        if len(p.get("authors") or []) > 3:
            authors += " et al."
        pdf_url = ""
        if p.get("openAccessPdf"):
            pdf_url = p["openAccessPdf"].get("url", "")
        papers.append({
            "paperId": p.get("paperId", ""),
            "arxivId": arxiv_id,
            "title": p.get("title", ""),
            "authors": authors,
            "year": p.get("year"),
            "citationCount": p.get("citationCount", 0),
            "abstract": (p.get("abstract") or "")[:300],
            "pdfUrl": pdf_url,
        })

    return json.dumps({"total": data.get("total", 0), "results": papers}, ensure_ascii=False, indent=2)


@mcp.tool()
def paper_details(paper_id: str) -> str:
    """Get detailed information about a paper including citations and references.

    Args:
        paper_id: Semantic Scholar paper ID, arXiv ID (prefix with 'arXiv:'), or DOI (prefix with 'DOI:')
    """
    fields = "title,authors,year,abstract,citationCount,referenceCount,externalIds,openAccessPdf,fieldsOfStudy"
    url = f"{_API_BASE}/paper/{urllib.parse.quote(paper_id)}?fields={fields}"

    try:
        paper = _api_get(url)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch paper: {e}"})

    arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
    authors = ", ".join(a.get("name", "") for a in (paper.get("authors") or []))

    citations_url = f"{_API_BASE}/paper/{urllib.parse.quote(paper_id)}/citations?fields=title,year,citationCount&limit=5"
    references_url = f"{_API_BASE}/paper/{urllib.parse.quote(paper_id)}/references?fields=title,year,citationCount&limit=5"

    try:
        citations_data = _api_get(citations_url)
        citations = [
            {"title": c["citingPaper"].get("title", ""), "year": c["citingPaper"].get("year"), "citations": c["citingPaper"].get("citationCount", 0)}
            for c in citations_data.get("data", []) if c.get("citingPaper")
        ]
    except Exception:
        citations = []

    try:
        references_data = _api_get(references_url)
        references = [
            {"title": r["citedPaper"].get("title", ""), "year": r["citedPaper"].get("year"), "citations": r["citedPaper"].get("citationCount", 0)}
            for r in references_data.get("data", []) if r.get("citedPaper")
        ]
    except Exception:
        references = []

    result = {
        "paperId": paper.get("paperId", ""),
        "arxivId": arxiv_id,
        "title": paper.get("title", ""),
        "authors": authors,
        "year": paper.get("year"),
        "abstract": paper.get("abstract", ""),
        "citationCount": paper.get("citationCount", 0),
        "referenceCount": paper.get("referenceCount", 0),
        "fieldsOfStudy": paper.get("fieldsOfStudy", []),
        "topCitations": citations,
        "topReferences": references,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
