import os
import base64

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured")

if not GROQ_VISION_MODEL:
    raise RuntimeError("GROQ_VISION_MODEL is not configured")

client = Groq(
    api_key=GROQ_API_KEY,
    timeout=30.0,
    max_retries=2,
)


def analyze_food_image(image_bytes: bytes) -> str:
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Identify the visible food ingredients in this image. "
                            "Return only a JSON object with this structure: "
                            '{"ingredients":["tomato","onion"]}. '
                            "Do not include explanations or markdown."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                ],
            }
        ],
        max_tokens=500,
        temperature=0.2,
    )

    return response.choices[0].message.content
