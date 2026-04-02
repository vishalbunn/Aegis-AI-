from agents.model import call_model
import json, re

def consensus_agent(query: str, pro: str, con: str, critique: str, final: str, round_num: int = 1) -> dict:
    prompt = f"""You are reviewing a multi-agent decision analysis (Round {round_num} of up to 3).

Query: {query}
PRO: {pro[:400]}
CON: {con[:400]}
CRITIQUE: {critique[:400]}
CURRENT FINAL: {final}

Stabilise and converge the answer. Be direct and decisive.

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "consensus": "A clear, direct 2-3 sentence final decision. Start with a clear recommendation.",
  "stability": 0-100,
  "key_points": ["most critical consideration 1", "most critical consideration 2", "most critical consideration 3"],
  "changed": true or false
}}

Stability guide: 90-100=fully converged, 70-89=mostly stable, 50-69=some disagreement, below 50=needs more rounds.
changed=true if your consensus meaningfully differs from CURRENT FINAL.
Return ONLY the JSON object."""

    raw = call_model(prompt)
    try:
        clean = re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"[consensus_agent] parse failed: {e} | raw: {raw[:200]}")

    return {"consensus": final, "stability": 70, "key_points": [], "changed": False}