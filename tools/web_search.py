"""Tool: web_search — Search the web via DuckDuckGo."""

import re
import urllib.request
from tools.registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for information about a paper, method, or code repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                }
            },
            "required": ["query"],
        },
    },
}


def handler(query: str) -> str:
    try:
        encoded_query = urllib.request.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        results = []
        blocks = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        for href, title, snippet in blocks[:5]:
            title = re.sub(r"<[^>]+>", "", title).strip()
            snippet = re.sub(r"<[^>]+>", "", snippet).strip()
            results.append(f"- {title}\n  {snippet}\n  URL: {href}")

        if results:
            return "\n\n".join(results)
        return "No results found. Try a different query."

    except Exception as e:
        return f"Error searching: {e}"


register("web_search", DEFINITION, handler)
