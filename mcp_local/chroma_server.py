"""MCP Server: ChromaDB — Vector database for paper semantic search (RAG)."""

import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

import chromadb

mcp = FastMCP(
    "chroma",
    instructions="Store and semantically search academic papers using vector embeddings.",
)

CHROMA_PATH = Path(__file__).parent.parent / "knowledge" / "chroma_db"
_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
_collection = _client.get_or_create_collection(
    name="papers",
    metadata={"description": "Paper abstracts and titles for semantic search"},
)


@mcp.tool()
def store_paper(paper_id: str, title: str, abstract: str, metadata: str = "{}") -> str:
    """Store a paper's embedding in the vector database for future semantic search.

    Args:
        paper_id: Unique paper identifier (e.g. arXiv ID '2310.06625')
        title: Paper title
        abstract: Paper abstract or summary
        metadata: Optional JSON string with extra fields (e.g. '{"year": 2024, "category": "Transformer"}')
    """
    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}

    meta["title"] = title
    document = f"{title}\n\n{abstract}"

    _collection.upsert(
        ids=[paper_id],
        documents=[document],
        metadatas=[meta],
    )

    total = _collection.count()
    return f"Stored paper '{title}' (ID: {paper_id}). Total papers in vector DB: {total}"


@mcp.tool()
def search_similar_papers(query: str, n_results: int = 5) -> str:
    """Search for semantically similar papers in the vector database.

    Args:
        query: Search query in natural language (e.g. 'attention mechanism alternatives for time series')
        n_results: Number of results to return (default 5)
    """
    total = _collection.count()
    if total == 0:
        return json.dumps({"results": [], "message": "Vector database is empty. Store papers first using store_paper."})

    n_results = min(n_results, total)
    results = _collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    papers = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for i, paper_id in enumerate(ids):
        papers.append({
            "paper_id": paper_id,
            "title": metadatas[i].get("title", "") if i < len(metadatas) else "",
            "similarity": round(1 - distances[i], 4) if i < len(distances) else 0,
            "excerpt": documents[i][:200] if i < len(documents) else "",
            "metadata": metadatas[i] if i < len(metadatas) else {},
        })

    return json.dumps({"query": query, "total_in_db": total, "results": papers}, ensure_ascii=False, indent=2)


@mcp.tool()
def list_stored_papers() -> str:
    """List all papers currently stored in the vector database."""
    total = _collection.count()
    if total == 0:
        return json.dumps({"total": 0, "papers": [], "message": "Vector database is empty."})

    data = _collection.get(limit=100)
    papers = []
    for i, paper_id in enumerate(data.get("ids", [])):
        meta = data["metadatas"][i] if i < len(data.get("metadatas", [])) else {}
        papers.append({
            "paper_id": paper_id,
            "title": meta.get("title", ""),
            "year": meta.get("year", ""),
            "category": meta.get("category", ""),
        })

    return json.dumps({"total": total, "papers": papers}, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
