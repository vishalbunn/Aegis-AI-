from agents.model import call_model

def baseline_agent(query: str) -> dict:
    """
    Single LLM call — no multi-agent pipeline.
    Used for baseline comparison against the full Aegis system.
    Returns: { "response": str, "word_count": int, "has_pros": bool, "has_cons": bool, "has_verdict": bool }
    """
    prompt = f"""You are a helpful AI assistant. A user is asking for help with a decision.

Decision: {query}

Please provide a thorough analysis covering:
- Pros and benefits
- Cons and risks
- Your final recommendation

Be as helpful and comprehensive as possible."""

    response = call_model(prompt)
    text = response.lower()

    return {
        "response": response,
        "word_count": len(response.split()),
        "has_pros": any(w in text for w in ["pro", "benefit", "advantage", "good"]),
        "has_cons": any(w in text for w in ["con", "risk", "disadvantage", "downside"]),
        "has_verdict": any(w in text for w in ["recommend", "suggest", "should", "decision", "conclude"]),
        "has_bias_check": False,
        "has_uncertainty_check": False,
        "has_scoring": False,
        "has_multi_agent": False,
    }
