import contextlib
import sqlite3
import uuid as uuid_mod
from pathlib import Path

from memebase.db import (
    add_tags,
    delete_meme_row,
    find_by_sha256,
    get_meme,
    get_meme_filename,
    insert_meme,
    update_description,
    update_filename,
)
from memebase.log import get_logger
from memebase.schemas import AiSuggestion, Meme, MemeError
from memebase.thumbnails import delete_thumbnails
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
    existing_id = find_by_sha256(conn, h)
    if existing_id:
        return get_meme(conn, existing_id), True

    new_id = str(uuid_mod.uuid4())
    file_size = file_path.stat().st_size
    basename = file_path.name
    ext = parse_ext(basename)
    insert_meme(conn, new_id, h, file_size, basename, ext)
    return get_meme(conn, new_id), False


def get_meme_file_path(
    conn: sqlite3.Connection, meme_id: str, memes_dir: Path
) -> tuple[str | None, Path | None, str | None]:
    """Look up filename and verify file exists on disk.

    Returns (filename, path, error_reason).
    error_reason is None on success, "not_in_db" or "not_on_disk" on failure.
    """
    filename = get_meme_filename(conn, meme_id)
    if not filename:
        return None, None, MemeError.NOT_IN_DB
    path = memes_dir / filename
    if not path.exists():
        return filename, path, MemeError.NOT_ON_DISK
    return filename, path, None


def rename_meme(
    conn: sqlite3.Connection,
    meme_id: str,
    filename: str,
    new_name_stem: str,
    memes_dir: Path,
) -> str:
    """Rename a meme file on disk and in the DB.

    Returns the new filename.
    Raises ValueError if stem is empty or unchanged, FileExistsError on collision.
    """
    orig = Path(filename)
    if not new_name_stem.strip():
        raise ValueError("Name cannot be empty")
    new_filename = sanitize_filename(new_name_stem + orig.suffix)
    new_stem = Path(new_filename).stem

    if new_stem == orig.stem:
        raise ValueError("Name is unchanged")

    new_path = memes_dir / new_filename
    if new_path.exists():
        raise FileExistsError("A file with that name already exists")

    (memes_dir / filename).rename(new_path)
    ext = parse_ext(new_filename)
    update_filename(conn, meme_id, new_filename, ext)
    return new_filename


def delete_meme(
    conn: sqlite3.Connection,
    meme_id: str,
    memes_dir: Path,
) -> str:
    """Delete a meme from DB and disk.

    Returns the deleted filename.
    Raises LookupError if the meme_id is not found in the DB.
    """
    filename = delete_meme_row(conn, meme_id)
    if not filename:
        raise LookupError("Not found")
    path = memes_dir / filename
    if path.exists():
        path.unlink()
    delete_thumbnails(meme_id)
    return filename


def apply_ai_suggestions(
    conn: sqlite3.Connection,
    meme_id: str,
    filename: str,
    suggestion: AiSuggestion,
    fields: list[str],
    memes_dir: Path,
) -> None:
    """Apply AI-suggested name/description/tags to a meme."""
    if "name" in fields and suggestion.get("name"):
        with contextlib.suppress(FileExistsError, ValueError):
            rename_meme(conn, meme_id, filename, suggestion["name"].strip(), memes_dir)

    if "description" in fields and suggestion.get("description"):
        update_description(conn, meme_id, suggestion["description"])

    if "tags" in fields and suggestion.get("tags"):
        add_tags(conn, meme_id, suggestion["tags"])
