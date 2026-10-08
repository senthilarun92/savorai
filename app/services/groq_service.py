import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured")

if not GROQ_TEXT_MODEL:
    raise RuntimeError("GROQ_TEXT_MODEL is not configured")

client = Groq(
    api_key=GROQ_API_KEY,
    timeout=30.0,
    max_retries=2,
)


def generate_text(prompt: str) -> str:
    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=1200,
        temperature=0.7,
    )

    return response.choices[0].message.content
