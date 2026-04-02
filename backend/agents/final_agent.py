from agents.model import call_model

def final_agent(query: str, pros: str, cons: str, critique: str) -> str:
    prompt = f"""You are the final decision-maker synthesizing a multi-agent analysis.

Query: {query}

PRO: {pros}
CON: {cons}
CRITIQUE: {critique}

Stay strictly on topic. Give:
- A clear Decision (yes/no/conditional)
- Reason (2-3 sentences)
- Confidence % (how sure are you)

Be direct and decisive."""

    return call_model(prompt)