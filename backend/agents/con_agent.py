from agents.model import call_model
from tools.search import search, format_for_prompt

def con_agent(query: str, use_tools: bool = False, domain_hint: str = "") -> str:
    search_context = ""
    if use_tools:
        results = search(f"{query} risks disadvantages problems 2025")
        search_context = f"\n\nREAL-WORLD DATA:\n{format_for_prompt(results)}\n"

    prompt = f"""You are an expert analyst building the strongest possible case AGAINST this decision.
{domain_hint}
Decision: {query}
{search_context}
Why is this a BAD idea? Use real data if provided.
Structure your response as a numbered list of clear, specific points.
Each point: Bold title: explanation.
Be thorough — 5-8 points."""

    return call_model(prompt)