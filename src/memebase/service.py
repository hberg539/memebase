import sqlite3
import uuid as uuid_mod
from pathlib import Path

from memebase.db import find_by_sha256, get_meme, get_meme_filename, insert_meme
from memebase.schemas import Meme, MemeError
from memebase.util import file_hash


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
