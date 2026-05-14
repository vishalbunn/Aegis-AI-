import re
from typing import List, Dict

def _tokenize(text: str) -> set:
    """Simple word tokenizer — no external deps needed."""
    words = re.findall(r'\b\w+\b', text.lower())
    stopwords = {'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'should',
                 'would', 'could', 'do', 'does', 'my', 'me', 'to', 'in', 'of',
                 'and', 'or', 'but', 'if', 'it', 'this', 'that', 'for', 'with'}
    return {w for w in words if w not in stopwords and len(w) > 2}

def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def find_similar(query: str, history: List[Dict], threshold: float = 0.3, top_k: int = 3) -> List[Dict]:
    """
    Find past decisions similar to the current query.
    Returns list of { id, query, final, similarity, created_at }
    """
    scored = []
    for item in history:
        sim = jaccard_similarity(query, item.get("query", ""))
        if sim >= threshold:
            scored.append({
                "id": item.get("id"),
                "query": item.get("query"),
                "final": (item.get("final") or "")[:200],
                "similarity": round(sim, 2),
                "created_at": item.get("created_at"),
            })
    return sorted(scored, key=lambda x: x["similarity"], reverse=True)[:top_k]

def detect_changed(query: str, similar: List[Dict]) -> str:
    """
    If we've seen a similar query before, note what might have changed.
    Returns a short string or empty string.
    """
    if not similar:
        return ""
    best = similar[0]
    if best["similarity"] > 0.6:
        return f"Very similar to past query (#{best['id']}): \"{best['query']}\". Previous decision: {best['final'][:100]}…"
    elif best["similarity"] > 0.3:
        return f"Somewhat related to past query (#{best['id']}): \"{best['query']}\"."
    return ""