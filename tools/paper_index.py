"""Tool: paper_index — Save and query the paper knowledge base."""

import json
from tools.common import PAPERS_INDEX_PATH
from tools.registry import register

DEFINITION_SAVE = {
    "type": "function",
    "function": {
        "name": "save_paper_index",
        "description": "Save a paper's structured information to the knowledge base. Call this after analyzing a paper to remember it across sessions.",
        "parameters": {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "arXiv ID (e.g. '2310.06625') or other unique identifier",
                },
                "title": {
                    "type": "string",
                    "description": "Paper title",
                },
                "authors": {
                    "type": "string",
                    "description": "First author et al.",
                },
                "year": {
                    "type": "integer",
                    "description": "Publication year",
                },
                "category": {
                    "type": "string",
                    "description": "Model category (e.g. 'Transformer-based', 'Linear', 'CNN', 'Foundation Model')",
                },
                "innovation": {
                    "type": "string",
                    "description": "One-sentence summary of the core innovation",
                },
                "datasets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Datasets used in experiments",
                },
                "metrics": {
                    "type": "object",
                    "description": "Key results, e.g. {\"ETTh1_MSE\": 0.37, \"Weather_MAE\": 0.21}",
                },
                "has_code": {
                    "type": "boolean",
                    "description": "Whether open-source code is available",
                },
                "repo_url": {
                    "type": "string",
                    "description": "GitHub repo URL if available",
                },
            },
            "required": ["arxiv_id", "title", "category", "innovation"],
        },
    },
}

DEFINITION_QUERY = {
    "type": "function",
    "function": {
        "name": "query_paper_index",
        "description": "Search the knowledge base for papers. Returns all papers or filters by category/keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword (matches title, category, or innovation). Leave empty to list all.",
                }
            },
            "required": [],
        },
    },
}


def _load_papers_index() -> list:
    if not PAPERS_INDEX_PATH.exists():
        return []
    try:
        return json.loads(PAPERS_INDEX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return []


def _save_papers_index_file(papers: list) -> None:
    PAPERS_INDEX_PATH.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")


def save_paper_index(
    arxiv_id: str,
    title: str,
    category: str,
    innovation: str,
    authors: str = "",
    year: int = 0,
    datasets: list = None,
    metrics: dict = None,
    has_code: bool = False,
    repo_url: str = "",
) -> str:
    papers = _load_papers_index()

    existing_idx = None
    for i, p in enumerate(papers):
        if p.get("arxiv_id") == arxiv_id:
            existing_idx = i
            break

    entry = {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "year": year,
        "category": category,
        "innovation": innovation,
        "datasets": datasets or [],
        "metrics": metrics or {},
        "has_code": has_code,
        "repo_url": repo_url,
    }

    if existing_idx is not None:
        papers[existing_idx] = entry
        action = "Updated"
    else:
        papers.append(entry)
        action = "Added"

    _save_papers_index_file(papers)
    return f"{action} paper '{title}' (ID: {arxiv_id}) to knowledge base. Total papers: {len(papers)}"


def query_paper_index(keyword: str = "") -> str:
    papers = _load_papers_index()

    if not papers:
        return "Knowledge base is empty. No papers have been indexed yet."

    if keyword:
        keyword_lower = keyword.lower()
        results = [
            p for p in papers
            if keyword_lower in p.get("title", "").lower()
            or keyword_lower in p.get("category", "").lower()
            or keyword_lower in p.get("innovation", "").lower()
            or keyword_lower in p.get("arxiv_id", "").lower()
        ]
    else:
        results = papers

    if not results:
        return f"No papers found matching '{keyword}'. Total papers in knowledge base: {len(papers)}"

    lines = [f"Found {len(results)} paper(s):\n"]
    for p in results:
        lines.append(f"- [{p.get('arxiv_id', '?')}] {p.get('title', 'Untitled')}")
        lines.append(f"  Category: {p.get('category', '?')} | Year: {p.get('year', '?')}")
        lines.append(f"  Innovation: {p.get('innovation', '?')}")
        if p.get("datasets"):
            lines.append(f"  Datasets: {', '.join(p['datasets'])}")
        if p.get("repo_url"):
            lines.append(f"  Code: {p['repo_url']}")
        lines.append("")

    return "\n".join(lines)


register("save_paper_index", DEFINITION_SAVE, save_paper_index)
register("query_paper_index", DEFINITION_QUERY, query_paper_index)
