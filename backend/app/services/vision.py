import os
import io
import base64
import json

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-haiku-5-5"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free fallbacks, only used if Claude fails
OPENROUTER_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
]

MAX_SIDE = 1568  # Claude's recommended max image dimension

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


def _prepare_image(image_bytes: bytes) -> tuple[str, str]:
    """
    Downscales large phone photos and re-encodes as JPEG so every model gets
    a small, consistent image. Returns (base64_data, media_type).
    """
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"


def _parse_json(raw_content: str) -> dict:
    raw_content = raw_content.strip()
    if raw_content.startswith("```"):
        raw_content = raw_content.strip("`")
        if raw_content.startswith("json"):
            raw_content = raw_content[4:].strip()
    return json.loads(raw_content)


def _call_claude(image_b64: str, media_type: str) -> dict:
    response = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 400,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": ANALYSIS_PROMPT},
                    ],
                }
            ],
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Claude failed ({response.status_code}): {response.text}")

    result = response.json()
    raw_content = result["content"][0]["text"]
    return _parse_json(raw_content)


def _call_openrouter(model: str, image_b64: str, media_type: str) -> dict:
    data_url = f"data:{media_type};base64,{image_b64}"
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
        raise RuntimeError(f"{model} rate-limited (429)")
    if response.status_code != 200:
        raise RuntimeError(f"{model} failed ({response.status_code}): {response.text}")

    result = response.json()
    raw_content = result["choices"][0]["message"]["content"]
    return _parse_json(raw_content)


def analyze_plant_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """
    Sends a photo to Claude first and returns a structured stress assessment.
    Falls back to free OpenRouter models if Claude is unavailable.
    """
    if not ANTHROPIC_API_KEY and not OPENROUTER_API_KEY:
        raise ValueError(
            "No vision API key set. Add ANTHROPIC_API_KEY (or OPENROUTER_API_KEY) to your environment."
        )

    try:
        image_b64, media_type = _prepare_image(image_bytes)
    except Exception as e:
        raise ValueError(f"Could not read the image: {e}")

    last_error = None

    if ANTHROPIC_API_KEY:
        try:
            return _call_claude(image_b64, media_type)
        except (requests.RequestException, RuntimeError, json.JSONDecodeError, KeyError) as e:
            last_error = f"Claude: {e}"

    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                return _call_openrouter(model, image_b64, media_type)
            except (requests.RequestException, RuntimeError, json.JSONDecodeError, KeyError) as e:
                last_error = f"{model}: {e}"
                continue

    raise RuntimeError(
        f"All vision models failed or were rate-limited. Last error: {last_error}"
    )