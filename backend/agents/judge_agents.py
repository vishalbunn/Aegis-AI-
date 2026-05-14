"""
Judge-tier agents — adjudicate the debate using the stronger model.
"""
import json
import re
from agents.model import call_judge


def critic_agent(pros: str, cons: str, query: str) -> str:
    prompt = f"""You are a critical evaluator reviewing a multi-agent debate.

Query: {query}

PRO arguments (final round):
{pros}

CON arguments (final round):
{cons}

Evaluate critically:
- Strongest 2 PRO points and why
- Strongest 2 CON points and why
- Weakest assumption either side made
- What both sides missed
- Which side mounted the more rigorous case

Be specific. 4 short paragraphs."""
    return call_judge(prompt, temperature=0.3)


def final_agent(query: str, pros: str, cons: str, critique: str) -> dict:
    prompt = f"""Synthesize a multi-agent debate into a final verdict.

Query: {query}

PRO (final): {pros[:2000]}
CON (final): {cons[:2000]}
CRITIQUE: {critique[:1500]}

Return ONLY valid JSON:
{{
  "verdict": "yes" or "no" or "conditional",
  "reasoning": "2-3 specific sentences citing the strongest arguments",
  "confidence": 0-100,
  "conditions": ["condition 1", "condition 2"]
}}"""
    raw = call_judge(prompt, temperature=0.2)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"verdict": "conditional", "reasoning": raw[:500], "confidence": 50, "conditions": []}


def consensus_agent(query: str, pro: str, con: str, critique: str, final: dict, round_num: int = 1) -> dict:
    prompt = f"""You are stabilizing a multi-agent decision (round {round_num}/3).

Query: {query}
PRO: {pro[:600]}
CON: {con[:600]}
CRITIQUE: {critique[:600]}
CURRENT VERDICT: {final.get('verdict')} (confidence {final.get('confidence')}%)
Reasoning: {final.get('reasoning', '')[:400]}

Return ONLY valid JSON:
{{
  "consensus": "2-3 sentence stabilized recommendation",
  "stability": 0-100,
  "agrees_with_verdict": true or false,
  "key_points": ["point 1", "point 2", "point 3"]
}}

stability: 90+=converged, 70-89=mostly stable, <70=needs more rounds."""
    raw = call_judge(prompt, temperature=0.2)
    try:
        clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {
        "consensus": final.get("reasoning", ""),
        "stability": 70,
        "agrees_with_verdict": True,
        "key_points": [],
    }


def scoring_agent(query: str, final: dict, pro: str, con: str) -> dict:
    prompt = f"""Score this decision quantitatively. Be honest — extreme scores when warranted.

Query: {query}
Verdict: {final.get('verdict')} — {final.get('reasoning', '')[:300]}
Pro arguments: {pro[:600]}
Con arguments: {con[:600]}

Return ONLY valid JSON:
{{
  "feasibility": 0-100,
  "feasibility_reason": "one short sentence",
  "risk": 0-100,
  "risk_reason": "one short sentence",
  "confidence": 0-100,
  "confidence_reason": "one short sentence",
  "impact": 0-100,
  "impact_reason": "one short sentence",
  "cost": 0-100,
  "cost_reason": "one short sentence (100=very costly)",
  "overall": 0-100
}}"""
    raw = call_judge(prompt, temperature=0.2)
    try:
        clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {k: 50 for k in ["feasibility", "risk", "confidence", "impact", "cost", "overall"]}