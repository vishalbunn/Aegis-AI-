from agents.model import call_model
import json, re

def uncertainty_agent(query: str) -> dict:
    prompt = f"""Analyze this query for ambiguity: "{query}"

Return ONLY valid JSON:
{{
  "is_ambiguous": true or false,
  "clarifications": ["question 1", "question 2"],
  "confidence": 0-100
}}

- is_ambiguous = true if the query lacks important context
- clarifications = 0-3 short clarifying questions (empty if not ambiguous)
Return ONLY the JSON."""

    raw = call_model(prompt)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"is_ambiguous": False, "clarifications": [], "confidence": 50}