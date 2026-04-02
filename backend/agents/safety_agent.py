from agents.model import call_model

HARD_BLOCK = [
    "how to make", "how to build", "how to synthesize",
    "bomb", "explosive", "poison", "kill", "suicide", "self harm",
    "self-harm", "weapon", "hack", "malware", "ransomware",
    "child", "minor", "illegal drug", "cocaine", "meth",
]

def safety_agent(query: str) -> dict:
    """
    Gates the query before any agents run.
    Returns:
      { "safe": bool, "reason": str, "severity": "none|low|medium|high|block" }
    """
    q_lower = query.lower()

    # Hard block — no LLM call needed
    for term in HARD_BLOCK:
        if term in q_lower:
            return {
                "safe": False,
                "reason": f"Query contains potentially harmful content ('{term}'). Aegis AI cannot assist with this.",
                "severity": "block",
            }

    # Soft check via LLM
    prompt = f"""You are a safety classifier for a decision-support AI.

Query: "{query}"

Is this query safe to analyze? Consider:
- Requests for harmful, illegal, or unethical advice
- Self-harm or harm to others
- Clearly malicious intent

Return ONLY valid JSON:
{{
  "safe": true or false,
  "reason": "one sentence explanation",
  "severity": "none or low or medium or high or block"
}}

If safe, severity = "none". Return ONLY the JSON."""

    raw = call_model(prompt)
    try:
        import json, re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            # Normalize
            if result.get("severity") == "block" or not result.get("safe", True):
                result["safe"] = False
            return result
    except Exception:
        pass
    # Default to safe if classifier fails
    return {"safe": True, "reason": "Safety check inconclusive — proceeding.", "severity": "low"}

