from agents.model import call_model

def relevance_agent(query: str, response: str) -> str:
    prompt = f"""Query: {query}

Response: {response}

Is this response relevant to the query? Answer ONLY: YES or NO"""
    return call_model(prompt)