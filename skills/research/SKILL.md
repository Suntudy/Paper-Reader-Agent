---
name: research
description: "Search and analyze academic papers using arXiv, Semantic Scholar, and web search."
---

# Academic Paper Research

Search, retrieve, and analyze academic papers. This skill orchestrates your available tools into a complete research workflow.

## Available Tools for This Workflow

| Tool | Use For |
|------|---------|
| `web_search` | Find papers by topic, find code repos, blog posts |
| `fetch_arxiv` | Download and read a paper given its arXiv ID |
| `read_pdf` | Read a locally downloaded PDF file |
| `query_paper_index` | Check if you've already read a paper |
| `save_paper_index` | Save paper metadata to the knowledge base |
| `git_clone` | Clone a paper's code repository for analysis |
| `generate_diagram` | Visualize model architecture as Mermaid diagram |
| `mcp_semantic_scholar_search_papers` | **Preferred for paper search** — precise academic search via Semantic Scholar API |
| `mcp_semantic_scholar_paper_details` | Get citation count, references, and citing papers for a specific paper |
| `mcp_chroma_store_paper` | Store paper embedding in vector DB for semantic similarity search |
| `mcp_chroma_search_similar_papers` | Find semantically similar papers from the vector knowledge base |
| `mcp_chroma_list_stored_papers` | List all papers in the vector knowledge base |

## Complete Research Workflow

**Always follow this order, even if the user only says "搜索/search":**

1. **Check existing knowledge first**: call `query_paper_index(keyword="...")` and `mcp_chroma_search_similar_papers(query="...")` to see if you've already read related papers
2. **Search**: use `mcp_semantic_scholar_search_papers(query="...")` as the primary search tool (returns precise academic results with citation counts). Fall back to `web_search` only if Semantic Scholar is unavailable
3. **Retrieve**: use `fetch_arxiv(arxiv_id="...")` to download and read each paper found — **do not skip this step**, searching without reading is useless
4. **Analyze**: extract structured information (title, authors, method, innovation, datasets, metrics)
5. **Save**: call `save_paper_index(...)` with all structured fields AND `mcp_chroma_store_paper(...)` to store embedding — never skip this step
6. **Summarize**: in your final response, provide a structured summary for the user:
   - Each paper: title, year, core innovation (one sentence), key results
   - If multiple papers: a comparison table
   - Your recommendation on which papers are most worth deep-reading
7. **Code**: if open-source, use `git_clone` to download and analyze the implementation
8. **Visualize**: use `generate_diagram` to draw the model architecture

**Important**: Steps 1-6 are mandatory for every research task. Steps 7-8 are optional based on user's request.

## Search Strategies

### By topic

Use `web_search` with targeted queries:
- `"arxiv {topic} 2024 site:arxiv.org"` — find recent papers on arXiv
- `"{method name} time series forecasting paper"` — find specific methods
- `"{paper title} github code"` — find code repositories
- `"NeurIPS 2024 time series foundation model"` — find by venue + year

### By arXiv ID

If you already have an ID like `2310.06625`, call `fetch_arxiv` directly. No need to search.

### By author

- `"arxiv {author name} time series"` — via web_search
- `"semantic scholar {author name}"` — find author profile and full paper list

### For non-arXiv papers

Many classic papers (e.g., LSTM 1997) are not on arXiv. In this case:
- Search for the PDF: `"{paper title} pdf"`
- If user has the PDF locally, use `read_pdf` directly
- Tell the user if you cannot access the paper

## arXiv Search Tips

### Query patterns that work well with web_search

| Goal | Query Template |
|------|---------------|
| Recent papers on a topic | `"arxiv {topic} 2024 2025"` |
| Papers by author | `"arxiv {author} {topic}"` |
| Papers from venue | `"{venue} 2024 {topic} arxiv"` |
| Specific paper | `"arxiv {exact title}"` |
| Code for a paper | `"{paper title} github"` |

### Common arXiv categories

| Category | Field |
|----------|-------|
| cs.LG | Machine Learning |
| cs.AI | Artificial Intelligence |
| cs.CL | NLP / Computation and Language |
| cs.CV | Computer Vision |
| stat.ML | Statistical Machine Learning |

## Using Semantic Scholar for Citations

Semantic Scholar provides citation data that arXiv doesn't. Search via `web_search`:

- `"semantic scholar {paper title}"` — find citation count, related papers
- `"semantic scholar {paper title} citations"` — who cited this paper
- `"semantic scholar {paper title} references"` — what this paper cites

This is useful for:
- Assessing paper impact (citation count)
- Finding follow-up work
- Discovering related papers you haven't read

## Output Expectations

**Your final response to the user MUST include a structured summary. Never end with just "已保存到知识库" — the user needs to see what you found.**

Required output format:

1. **Overview** — how many papers found, what the topic covers
2. **Paper list with summaries** — for each paper:
   - Title, authors, year
   - Core innovation (one sentence in Chinese)
   - Key results/metrics if available
3. **Comparison table** — if 2+ papers, include a Markdown table comparing methods/datasets/metrics/innovation
4. **Recommendation** — which papers are most worth reading in depth, and why
5. **Knowledge base status** — confirm papers have been saved via `save_paper_index`

## Example Workflows

### "Find papers on time series foundation models"

```
1. query_paper_index(keyword="foundation model") → check what you already know
2. web_search(query="arxiv time series foundation model 2024 2025") → find papers
3. For each promising result:
   a. fetch_arxiv(arxiv_id="...") → download and read
   b. save_paper_index(...) → save to knowledge base
4. Generate comparison table of all found papers
5. generate_diagram for the most interesting architecture
```

### "Read PatchTST and analyze its code"

```
1. query_paper_index(keyword="PatchTST") → already read?
2. fetch_arxiv(arxiv_id="2211.14730") → download paper
3. save_paper_index(...) → save metadata
4. web_search(query="PatchTST github") → find repo
5. git_clone(repo_url="...") → clone code
6. list_files + read_file → examine model implementation
7. generate_diagram(title="PatchTST_architecture", ...) → visualize
```

## Notes

- arXiv rate limit: ~1 request per 3 seconds. Don't batch-fetch too many papers at once.
- Always save papers to the knowledge base. This is how the agent builds memory across sessions.
- When the user speaks Chinese, respond in Chinese.
