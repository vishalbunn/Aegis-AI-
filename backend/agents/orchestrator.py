from agents.model import call_model
import re

def orchestrator(query: str) -> dict:
    """
    Scores query complexity and returns routing config.
    Returns:
    {
      "complexity": "simple|moderate|complex",
      "complexity_score": 0-100,
      "run_bias": bool,
      "run_consensus_rounds": int,   # 1, 2, or 3
      "run_tools": bool,
      "reason": str
    }
    """
    prompt = f"""Analyze this decision query and determine how complex it is.

Query: "{query}"

Consider:
- Is it a personal, low-stakes decision? (simple)
- Does it involve finances, career, or health tradeoffs? (moderate)
- Is it multi-dimensional, domain-specific, or high-stakes? (complex)

Return ONLY valid JSON:
{{
  "complexity": "simple or moderate or complex",
  "complexity_score": 0-100,
  "run_bias": true or false,
  "run_consensus_rounds": 1 or 2 or 3,
  "run_tools": true or false,
  "reason": "one sentence why"
}}

Rules:
- simple (score 0-35): 1 consensus round, no bias check, no tools
- moderate (score 36-65): 2 consensus rounds, bias check, maybe tools
- complex (score 66-100): 3 consensus rounds, bias check, tools always
- run_tools = true if query would benefit from real-world data (market, news, trends)
Return ONLY the JSON."""

    raw = call_model(prompt)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            import json
            result = json.loads(match.group())
            score = result.get("complexity_score", 50)
            # Enforce consistency
            if score <= 35:
                result.update({"complexity": "simple", "run_bias": False, "run_consensus_rounds": 1, "run_tools": False})
            elif score <= 65:
                result.update({"complexity": "moderate", "run_bias": True, "run_consensus_rounds": 2})
            else:
                result.update({"complexity": "complex", "run_bias": True, "run_consensus_rounds": 3, "run_tools": True})
            return result
    except Exception:
        pass
    # Default: moderate
    return {
        "complexity": "moderate",
        "complexity_score": 50,
        "run_bias": True,
        "run_consensus_rounds": 2,
        "run_tools": False,
        "reason": "Routing defaulted to moderate.",
    }


