import base64
import json
import logging
import mimetypes
import re

import litellm

from memebase.schemas import AiSuggestion

log = logging.getLogger(__name__)


def build_prompt(template: str, existing_tags: list[str]) -> str:
    """Substitute {tags} placeholder in the prompt template."""
    return template.replace("{tags}", ", ".join(existing_tags))


def encode_image(image_path: str) -> tuple[str, str]:
    """Read an image file and return (mime_type, base64_data)."""
    mime, _ = mimetypes.guess_type(image_path)
    if mime is None:
        mime = "image/png"
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    return mime, image_data


def parse_ai_response(raw_text: str) -> AiSuggestion:
    """Strip markdown code fences and parse JSON from AI response text."""
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return json.loads(stripped)


def analyze_meme(
    image_path: str, existing_tags: list[str], *, model: str, prompt_template: str
) -> AiSuggestion:
    prompt = build_prompt(prompt_template, existing_tags)

    mime, image_data = encode_image(image_path)

    response = litellm.completion(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_data}",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.choices[0].message.content
    log.debug("ai response: model=%s length=%d body=%s", model, len(raw), raw)

    return parse_ai_response(raw)
