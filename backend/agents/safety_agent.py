"""
Safety agent v5.1

v4 bug: substring keyword match (blocked 'should I have a child').
v5 bug: LLM classifier over-blocked risky personal decisions (e.g. 'should I put 80% of my
        savings in BTC' — that's a risky decision, not a harmful query).
v5.1 fix: prompt explicitly distinguishes "harm to others/self via operational instructions"
          (block) from "risky personal choice" (allow — that's what the system is FOR).
"""
import re
import json
from agents.model import call_debater

HARD_BLOCK_PHRASES = [
    r"\bhow to (make|build|synthesize|create) (a )?(bomb|explosive|poison|weapon|gun|firearm)\b",
    r"\b(synthesize|cook|make) (meth|cocaine|heroin|fentanyl)\b",
    r"\bhow (do i|to) (kill|murder|harm) (someone|a person|people|him|her|them)\b",
    r"\bcsam\b|\bchild (porn|sexual|sex)\b|\bsexual.{0,10}(minor|child)\b",
    r"\bhow to (commit|plan) (suicide|self.?harm)\b",
    r"\b(write|build|create|generate) (malware|ransomware|a virus|a trojan)\b",
]


def safety_agent(query: str) -> dict:
    q_lower = query.lower()

    for pattern in HARD_BLOCK_PHRASES:
        if re.search(pattern, q_lower):
            return {
                "safe": False,
                "reason": "Query matches a hard-block pattern for harmful content.",
                "severity": "block",
                "matched": pattern,
            }

    prompt = f"""You are a safety classifier for Aegis, a DECISION-SUPPORT system that helps users think through hard personal/business/financial/medical/career choices.

Query: "{query}"

CRITICAL: Aegis is built TO HELP WITH RISKY DECISIONS. Risk is the POINT. Do NOT block a query just because the decision is risky, ill-advised, contrarian, or could lead to financial/health/personal loss. Those are exactly the queries Aegis needs to answer — the system's job is to argue both sides so the user makes a better decision.

ALWAYS SAFE (do not block, regardless of how reckless they sound):
- Putting large fractions of net worth in any asset (crypto, stocks, real estate, single company)
- Quitting a job, dropping out of school, ending a marriage, having/not having children
- Refusing/delaying medical treatment, alternative medicine, controversial diets
- Taking on large debt, leveraged trades, gambling
- Confronting people, cutting off relationships, moving countries
- Career changes that look financially irrational
- Buying weapons legally, using legal drugs, recreational substances
- Discussing extremism/terrorism/violence in research, policy, or analytical framing

BLOCK ONLY (severity = block):
- Operational instructions to harm an identified person ("how do I kill my neighbor")
- Operational instructions to synthesize weapons/drugs ("how to make meth")
- Operational instructions to bypass security ("write malware that...")
- Sexual content involving minors
- Self-harm method requests ("how to commit suicide painlessly")

Return ONLY valid JSON:
{{"safe": true or false, "reason": "one short sentence — leave blank if safe", "severity": "none|low|medium|high|block"}}

Default to "safe": true. Block only the categories listed above."""

    raw = call_debater(prompt, temperature=0.0)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            # Only honor the LLM's unsafe verdict if severity is explicitly "block"
            if result.get("severity") == "block":
                result["safe"] = False
            else:
                result["safe"] = True
            return result
    except Exception:
        pass

    return {"safe": True, "reason": "", "severity": "low"}