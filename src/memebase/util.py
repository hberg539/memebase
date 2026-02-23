import hashlib
import logging
import re
import unicodedata

log = logging.getLogger(__name__)

# Characters forbidden on Windows (and generally problematic)
_RESERVED_CHARS = re.compile(r'[<>:"/\\|?*#%\x00-\x1f]')
# Windows reserved device names
_RESERVED_NAMES = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\.|$)", re.IGNORECASE)


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
