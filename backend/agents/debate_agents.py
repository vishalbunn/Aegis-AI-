"""
Debate agents — sequential mode.

Key change from v4: Pro and Con receive each other's previous-round arguments
and are instructed to refine, not just repeat. This is the difference between
"parallel monologue" (v4) and "actual debate" (v5).
"""
from agents.model import call_debater
from tools.search import search, format_for_prompt


def pro_agent(
    query: str,
    use_tools: bool = False,
    domain_hint: str = "",
    opponent_last: str = "",
    own_last: str = "",
    round_num: int = 1,
) -> str:
    search_context = ""
    if use_tools and round_num == 1:
        results = search(f"{query} benefits advantages")
        search_context = f"\n\nREAL-WORLD DATA:\n{format_for_prompt(results)}\n"

    if round_num == 1:
        prompt = f"""You are an analyst building the strongest case IN FAVOR of this decision.
{domain_hint}
Decision: {query}
{search_context}
Give 5-7 specific, concrete points. Format: **Bold title:** explanation.
Avoid generic platitudes — every point must be specific to THIS decision."""
    else:
        prompt = f"""You are continuing a debate IN FAVOR of this decision (round {round_num}).
{domain_hint}
Decision: {query}

YOUR PREVIOUS ARGUMENT:
{own_last[:1500]}

OPPONENT'S LATEST ARGUMENT (against):
{opponent_last[:1500]}

Now refine. You must:
1. Directly REBUT the strongest 1-2 points your opponent made.
2. STRENGTHEN your weakest point from your previous round.
3. Add 1-2 NEW considerations they missed.
Do NOT just repeat your previous arguments. Format: **Bold title:** explanation."""

    return call_debater(prompt, temperature=0.7)


def con_agent(
    query: str,
    use_tools: bool = False,
    domain_hint: str = "",
    opponent_last: str = "",
    own_last: str = "",
    round_num: int = 1,
) -> str:
    search_context = ""
    if use_tools and round_num == 1:
        results = search(f"{query} risks disadvantages problems")
        search_context = f"\n\nREAL-WORLD DATA:\n{format_for_prompt(results)}\n"

    if round_num == 1:
        prompt = f"""You are an analyst building the strongest case AGAINST this decision.
{domain_hint}
Decision: {query}
{search_context}
Give 5-7 specific, concrete points. Format: **Bold title:** explanation.
Avoid generic platitudes — every point must be specific to THIS decision."""
    else:
        prompt = f"""You are continuing a debate AGAINST this decision (round {round_num}).
{domain_hint}
Decision: {query}

YOUR PREVIOUS ARGUMENT:
{own_last[:1500]}

OPPONENT'S LATEST ARGUMENT (in favor):
{opponent_last[:1500]}

Now refine. You must:
1. Directly REBUT the strongest 1-2 points your opponent made.
2. STRENGTHEN your weakest point from your previous round.
3. Add 1-2 NEW considerations they missed.
Do NOT just repeat your previous arguments. Format: **Bold title:** explanation."""

    return call_debater(prompt, temperature=0.7)