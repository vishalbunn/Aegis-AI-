from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

def call_model(prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # 🔥 powerful + free
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Model Error: {str(e)}"