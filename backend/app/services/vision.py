import os
import base64
import json

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
]

ANALYSIS_PROMPT = """You are analyzing a close-up photo of a plant or crop for visible signs of stress.

Look for: discoloration (yellowing, browning), wilting, pest damage, holes in leaves,
spots, or other visible signs of poor plant health. Also look for signs of good health:
vibrant green color, full/turgid leaves, no visible damage.

Respond with ONLY a JSON object in this exact format, nothing else, no markdown formatting:
{
  "health_score": <integer 0-100, where 0 is severe stress/dead plant and 100 is perfectly healthy>,
  "summary": "<one short plain-language sentence describing what you see>",
  "issues_detected": ["<short tag>", "<short tag>"]
}

If no plant is clearly visible in the photo, set health_score to null and explain in summary.
"""


def analyze_plant_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """
    Sends a photo to a free vision-capable model via OpenRouter and returns
    a structured stress assessment. Tries each model in MODELS in order,
    falling back to the next if one is rate-limited or unavailable.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Add it to backend/.env"
        )

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{media_type};base64,{image_b64}"

    last_error = None

    for model in MODELS:
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": ANALYSIS_PROMPT},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                },
                timeout=30,
            )

            if response.status_code == 429:
                last_error = f"{model} rate-limited (429)"
                continue

            if response.status_code != 200:
                last_error = f"{model} failed ({response.status_code}): {response.text}"
                continue

            result = response.json()
            raw_content = result["choices"][0]["message"]["content"].strip()

            if raw_content.startswith("```"):
                raw_content = raw_content.strip("`")
                if raw_content.startswith("json"):
                    raw_content = raw_content[4:].strip()

            try:
                parsed = json.loads(raw_content)
            except json.JSONDecodeError:
                last_error = f"{model} returned invalid JSON: {raw_content}"
                continue

            return parsed

        except requests.RequestException as e:
            last_error = f"{model} request error: {e}"
            continue

    raise RuntimeError(
        f"All vision models failed or were rate-limited. Last error: {last_error}"
    )