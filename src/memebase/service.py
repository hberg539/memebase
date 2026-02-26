import sqlite3
import uuid as uuid_mod
from pathlib import Path

from memebase.db import (
    add_tags,
    find_by_sha256,
    get_meme,
    get_meme_filename,
    insert_meme,
    update_description,
    update_filename,
)
from memebase.log import get_logger
from memebase.schemas import AiSuggestion, Meme, MemeError
from memebase.util import file_hash, parse_ext, sanitize_filename

log = get_logger(__name__)


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
    ext = parse_ext(basename)
    insert_meme(conn, new_uuid, h, file_size, basename, ext)
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
            ext = parse_ext(new_filename)
            update_filename(conn, uuid, new_filename, ext)

    if "description" in fields and suggestion.get("description"):
        update_description(conn, uuid, suggestion["description"])

    if "tags" in fields and suggestion.get("tags"):
        add_tags(conn, uuid, suggestion["tags"])
