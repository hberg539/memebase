import sqlite3
import urllib.parse
import urllib.request
import uuid as uuid_mod
from pathlib import Path

from memebase.common import ALLOWED_EXTENSIONS, CONTENT_TYPE_TO_EXT, USER_AGENT
from memebase.db import (
    add_tags,
    find_by_sha256,
    get_meme,
    get_meme_filename,
    insert_meme,
    update_description,
    update_filename,
)
from memebase.schemas import AiSuggestion, Meme, MemeError
from memebase.util import file_hash, sanitize_filename


def resolve_unique_path(directory: Path, basename: str) -> tuple[Path, str]:
    """Return (dest_path, final_basename) avoiding filename collisions."""
    dest = directory / basename
    if dest.exists():
        p = Path(basename)
        counter = 1
        while dest.exists():
            dest = directory / f"{p.stem}_{counter}{p.suffix}"
            counter += 1
        basename = dest.name
    return dest, basename


def register_meme(conn: sqlite3.Connection, file_path: Path) -> tuple[Meme, bool]:
    """Hash file, check for duplicate, insert or return existing.

    Returns (meme_dict, is_duplicate).
    """
    h = file_hash(file_path)
    existing_uuid = find_by_sha256(conn, h)
    if existing_uuid:
        return get_meme(conn, existing_uuid), True

    new_uuid = str(uuid_mod.uuid4())
    file_size = file_path.stat().st_size
    basename = file_path.name
    insert_meme(conn, new_uuid, h, file_size, basename)
    return get_meme(conn, new_uuid), False


def get_meme_file_path(
    conn: sqlite3.Connection, uuid: str, memes_dir: Path
) -> tuple[str | None, Path | None, str | None]:
    """Look up filename and verify file exists on disk.

    Returns (filename, path, error_reason).
    error_reason is None on success, "not_in_db" or "not_on_disk" on failure.
    """
    filename = get_meme_filename(conn, uuid)
    if not filename:
        return None, None, MemeError.NOT_IN_DB
    path = memes_dir / filename
    if not path.exists():
        return filename, path, MemeError.NOT_ON_DISK
    return filename, path, None


def download_from_url(url: str) -> tuple[str, bytes]:
    """Download a file from a URL and return (sanitized_basename, content).

    Raises ValueError on bad scheme, unsupported extension, or download failure.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are supported")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Try Content-Disposition for filename
            cd = resp.headers.get("Content-Disposition", "")
            filename = None
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].strip().strip('"').strip("'")

            if not filename:
                path_part = urllib.parse.urlparse(url).path
                filename = Path(path_part).name or "download"

            # Ensure it has an allowed extension
            ext = Path(filename).suffix.lower()
            if not ext:
                ct = resp.headers.get("Content-Type", "")
                ext = CONTENT_TYPE_TO_EXT.get(ct.split(";")[0].strip(), "")
                filename += ext

            if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
                raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

            content = resp.read()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to download: {e}") from e

    return sanitize_filename(filename), content


def apply_ai_suggestions(
    conn: sqlite3.Connection,
    uuid: str,
    filename: str,
    suggestion: AiSuggestion,
    fields: list[str],
    memes_dir: Path,
) -> None:
    """Apply AI-suggested name/description/tags to a meme."""
    if "name" in fields and suggestion.get("name"):
        orig_ext = Path(filename).suffix
        new_filename = sanitize_filename(suggestion["name"].strip() + orig_ext)
        new_path = memes_dir / new_filename
        if new_filename != filename and not new_path.exists():
            (memes_dir / filename).rename(new_path)
            update_filename(conn, uuid, new_filename)

    if "description" in fields and suggestion.get("description"):
        update_description(conn, uuid, suggestion["description"])

    if "tags" in fields and suggestion.get("tags"):
        add_tags(conn, uuid, suggestion["tags"])
