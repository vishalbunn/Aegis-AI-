"""
Bias detection — actually called in v5 (was orphaned in v4).
"""
import json
import re
from agents.model import call_judge


COGNITIVE_BIASES = [
    "confirmation bias", "anchoring", "availability heuristic",
    "sunk cost fallacy", "survivorship bias", "optimism bias",
    "loss aversion", "status quo bias", "false consensus",
    "framing effect", "recency bias", "narrative fallacy",
]


def bias_agent(pro: str, con: str, query: str) -> dict:
    biases_str = ", ".join(COGNITIVE_BIASES)
    prompt = f"""Audit these debate arguments for cognitive bias from this list:
{biases_str}

Query: {query}

PRO arguments:
{pro[:2000]}

CON arguments:
{con[:2000]}

For each side, identify the SINGLE most prominent bias (or 'none detected').
Quote the specific phrase that exemplifies it.

Return ONLY valid JSON:
{{
  "pro_bias": {{
    "type": "bias name or 'none detected'",
    "evidence": "short quote from PRO that shows it",
    "severity": "low|medium|high"
  }},
  "con_bias": {{
    "type": "bias name or 'none detected'",
    "evidence": "short quote from CON that shows it",
    "severity": "low|medium|high"
  }},
  "overall_bias": "which side leans more biased, or 'balanced'",
  "flags": ["bias1", "bias2"]
}}"""
    raw = call_judge(prompt, temperature=0.2)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {
        "pro_bias": {"type": "none detected", "evidence": "", "severity": "low"},
        "con_bias": {"type": "none detected", "evidence": "", "severity": "low"},
        "overall_bias": "balanced",
        "flags": [],
    }