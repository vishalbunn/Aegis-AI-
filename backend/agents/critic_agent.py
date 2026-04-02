from agents.model import call_model

def critic_agent(pros: str, cons: str, query: str) -> str:
    prompt = f"""You are a critical evaluator reviewing a multi-agent debate.

Query: {query}

PRO arguments:
{pros}

CON arguments:
{cons}

Evaluate critically:
- What are the weaknesses in the PRO arguments?
- What are the weaknesses in the CON arguments?
- What important points are missing from both sides?
- How relevant is this analysis to the actual query?

Be concise and specific. 3-5 paragraphs."""

    return call_model(prompt)