"""
Search tool for Aegis AI agents.
Primary: Tavily API (set TAVILY_API_KEY in .env)
Fallback: DuckDuckGo HTML scraper (no key needed)
"""
import os
import re
import json
import urllib.request
import urllib.parse
from typing import List, Dict

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

def search(query: str, max_results: int = 5) -> List[Dict]:
    """
    Returns list of { title, url, content } dicts.
    Tries Tavily first, falls back to DuckDuckGo scraper.
    """
    if TAVILY_API_KEY:
        try:
            return _tavily_search(query, max_results)
        except Exception as e:
            print(f"[search] Tavily failed: {e} — falling back to DDG")
    return _ddg_search(query, max_results)


def _tavily_search(query: str, max_results: int) -> List[Dict]:
    url = "https://api.tavily.com/search"
    payload = json.dumps({
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    results = []
    if data.get("answer"):
        results.append({"title": "Summary", "url": "", "content": data["answer"]})
    for r in data.get("results", [])[:max_results]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:400],
        })
    return results


def _ddg_search(query: str, max_results: int) -> List[Dict]:
    """Lightweight DuckDuckGo HTML scraper — no API key needed."""
    q = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={q}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AegisAI/3.0)"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return [{"title": "Search unavailable", "url": "", "content": str(e)}]

    results = []
    snippets = re.findall(
        r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>',
        html, re.DOTALL
    )
    for url, title, snippet in snippets[:max_results]:
        results.append({
            "title": re.sub(r'<[^>]+>', '', title).strip(),
            "url": url,
            "content": re.sub(r'<[^>]+>', '', snippet).strip(),
        })
    if not results:
        results.append({"title": "No results", "url": "", "content": "Search returned no results."})
    return results


def format_for_prompt(results: List[Dict]) -> str:
    """Format search results into a compact string for agent prompts."""
    if not results:
        return "No search results available."
    lines = ["[Web Search Results]"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        if r.get("content"):
            lines.append(f"   {r['content'][:300]}")
    return "\n".join(lines)
