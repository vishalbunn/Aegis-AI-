from agents.model import call_model
import json, re

def scoring_agent(query: str, final: str, pro: str, con: str) -> dict:
    prompt = f"""Score this decision quantitatively. Be precise and realistic.

Query: {query}
Decision: {final}
Pro arguments: {pro[:500]}
Con arguments: {con[:500]}

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "feasibility": 0-100,
  "feasibility_reason": "one sentence max",
  "risk": 0-100,
  "risk_reason": "one sentence max",
  "confidence": 0-100,
  "confidence_reason": "one sentence max",
  "impact": 0-100,
  "impact_reason": "one sentence max",
  "cost": 0-100,
  "cost_reason": "one sentence max (100=very costly)",
  "overall": 0-100,
  "agent_influence": {{
    "pro_agent": 0-100,
    "con_agent": 0-100,
    "critic_agent": 0-100,
    "consensus_agent": 0-100
  }}
}}

CRITICAL: agent_influence values MUST sum to exactly 100. Example: pro=35, con=25, critic=20, consensus=20.
Return ONLY the JSON object, no other text."""

    raw = call_model(prompt)
    try:
        clean = re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            result = json.loads(match.group())

            # Fix agent_influence to always sum to 100
            inf = result.get("agent_influence", {})
            if inf:
                total = sum(inf.values())
                if total > 0 and total != 100:
                    # Normalize
                    result["agent_influence"] = {
                        k: round(v / total * 100) for k, v in inf.items()
                    }
                    # Fix rounding drift on largest value
                    normed = result["agent_influence"]
                    diff = 100 - sum(normed.values())
                    if diff != 0:
                        biggest = max(normed, key=normed.get)
                        normed[biggest] += diff

            return result
    except Exception as e:
        print(f"[scoring_agent] parse failed: {e} | raw: {raw[:200]}")

    return {
        "feasibility": 50, "feasibility_reason": "Unable to score.",
        "risk": 50, "risk_reason": "Unable to score.",
        "confidence": 50, "confidence_reason": "Unable to score.",
        "impact": 50, "impact_reason": "Unable to score.",
        "cost": 50, "cost_reason": "Unable to score.",
        "overall": 50,
        "agent_influence": {"pro_agent": 30, "con_agent": 30, "critic_agent": 20, "consensus_agent": 20}
    }