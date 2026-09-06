import hashlib
import io
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Characters forbidden on Windows (and generally problematic)
_RESERVED_CHARS = re.compile(r'[<>:"/\\|?*#%\x00-\x1f]')
# Windows reserved device names
_RESERVED_NAMES = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\.|$)", re.IGNORECASE)


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug: lowercase, hyphens, no special chars.

    Raises ValueError if the resulting slug is empty.
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    if not name:
        raise ValueError("Name produces an empty slug")
    return name


def parse_ext(filename: str) -> str:
    """Extract dotless lowercase extension from a filename (e.g. 'photo.PNG' -> 'png')."""
    return Path(filename).suffix.lstrip(".").lower()


def sanitize_filename(name: str) -> str:
    """Sanitize a filename to be safe on Windows, macOS, and Linux. UTF-8 allowed."""
    # Normalize unicode
    name = unicodedata.normalize("NFC", name)
    # Strip path separators and take basename
    name = name.replace("\\", "/")
    name = name.split("/")[-1]
    # Replace forbidden characters with underscore
    name = _RESERVED_CHARS.sub("_", name)
    # Strip leading/trailing dots and spaces (problematic on Windows)
    # Use rfind to split on the last dot so ".png" is treated as ext, not stem
    last_dot = name.rfind(".")
    if last_dot > 0:
        stem, ext = name[:last_dot], name[last_dot:]
    elif last_dot == 0:
        stem, ext = "", name
    else:
        stem, ext = name, ""
    stem = stem.strip(". ")
    # Handle Windows reserved names
    if _RESERVED_NAMES.match(stem):
        stem = "_" + stem
    name = stem + ext
    # Fallback if empty
    if not stem:
        name = "unnamed" + ext
    # Truncate to 200 bytes (well within 255-byte filesystem limits)
    last_dot = name.rfind(".")
    if last_dot > 0:
        stem, ext = name[:last_dot], name[last_dot:]
    else:
        stem, ext = name, ""
    max_stem = 200 - len(ext.encode("utf-8"))
    while len(stem.encode("utf-8")) > max_stem:
        stem = stem[:-1]
    name = stem + ext
    return name


def normalize_tags(tags: list[str]) -> set[str]:
    """Deduplicate and normalize a list of tags."""
    return {t.strip().lower() for t in tags} - {""}


def file_hash(path: str) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


_placeholder_image_bytes: bytes | None = None


def generate_placeholder_image() -> bytes:
    """Generate a dark 400x300 PNG with '404' text. Cached after first call."""
    global _placeholder_image_bytes
    if _placeholder_image_bytes is not None:
        return _placeholder_image_bytes

    w, h = 400, 300
    img = Image.new("RGB", (w, h), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    try:
        big = ImageFont.load_default(size=80)
        small = ImageFont.load_default(size=20)
    except TypeError:
        big = small = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "404", font=big)
    draw.text(((w - bbox[2]) / 2, (h - bbox[3]) / 2 - 20), "404", fill=(120, 120, 120), font=big)

    bbox = draw.textbbox((0, 0), "not found", font=small)
    draw.text(
        ((w - bbox[2]) / 2, (h + bbox[3]) / 2 + 30), "not found", fill=(90, 90, 90), font=small
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    _placeholder_image_bytes = buf.getvalue()
    return _placeholder_image_bytes
