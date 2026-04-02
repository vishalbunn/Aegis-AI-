import requests

def research_agent(query):
    prompt = f"""
    Analyze briefly:
    {query}

    Give:
    - Market
    - Audience
    - Competitors
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3:mini",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 30}
            },
            timeout=120
        )

        data = response.json()
        return data.get("response", str(data))

    except Exception as e:
        return f"Error: {str(e)}"