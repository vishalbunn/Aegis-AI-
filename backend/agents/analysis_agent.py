import requests

def analysis_agent(research):
    prompt = f"""
Based on this:
{research}

Give briefly:
- Pros
- Cons
- Feasibility

Keep it SHORT.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "phi3",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_predict": 120
            }
        }
    )

    return response.json()["response"]