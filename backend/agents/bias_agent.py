from agents.model import call_model
import json, re

def bias_agent(pro: str, con: str, query: str) -> dict:
    prompt = f"""Analyze these arguments for cognitive bias.

Query: {query}
PRO: {pro}
CON: {con}

Return ONLY valid JSON:
{{
  "pro_bias": "description or 'none detected'",
  "con_bias": "description or 'none detected'",
  "overall_bias": "which side is more biased or 'balanced'",
  "severity": "low or medium or high",
  "flags": ["bias type 1", "bias type 2"]
}}
Return ONLY the JSON."""

    raw = call_model(prompt)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"pro_bias": "none detected", "con_bias": "none detected", "overall_bias": "balanced", "severity": "low", "flags": []}