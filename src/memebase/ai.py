import base64
import json
import mimetypes
import re
from pathlib import Path

import litellm
from PIL import Image

from memebase.gif_frames import gif_content
from memebase.log import get_logger
from memebase.schemas import AiSuggestion

log = get_logger(__name__)


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


def _image_content(image_path: str, gif_frames: bool) -> list[dict]:
    if gif_frames and Path(image_path).suffix.lower() == ".gif":
        with Image.open(image_path) as image:
            if image.format == "GIF" and image.is_animated:
                return gif_content(image)
    mime, image_data = encode_image(image_path)
    return [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}}]


def analyze_meme(
    image_path: str,
    existing_tags: list[str],
    *,
    model: str,
    prompt_template: str,
    gif_frames: bool = True,
) -> AiSuggestion:
    prompt = build_prompt(prompt_template, existing_tags)
    content = _image_content(image_path, gif_frames)
    content.append({"type": "text", "text": prompt})

    response = litellm.completion(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.choices[0].message.content
    log.debug("ai response: model=%s length=%d body=%s", model, len(raw), raw)

    return parse_ai_response(raw)
