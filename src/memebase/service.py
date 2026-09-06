import contextlib
import sqlite3
import uuid as uuid_mod
from pathlib import Path

from memebase.db import (
    add_tags,
    delete_collection,
    delete_meme_row,
    find_by_sha256,
    get_collection,
    get_meme,
    get_meme_filename,
    insert_collection,
    insert_meme,
    update_collection,
    update_description,
    update_filename,
    update_meme_collection,
)
from memebase.log import get_logger
from memebase.probe import probe_file
from memebase.schemas import AiSuggestion, Meme, MemeError, SourceMeta
from memebase.thumbnails import delete_thumbnails
from memebase.util import file_hash, parse_ext, sanitize_filename, slugify

log = get_logger(__name__)


def meme_file_dir(memes_dir: Path, collection: str | None) -> Path:
    """Return the directory for meme files, scoped to a collection if given."""
    if collection:
        return memes_dir / collection
    return memes_dir


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


def resolve_collection(conn: sqlite3.Connection, slug: str | None) -> dict | None:
    """Resolve a client-supplied slug to its collections row ({id, slug, name}).

    Returns None for an empty slug (meaning "no collection").
    Raises LookupError if the slug does not match a collection. Paths must only
    ever be built from the slug stored in the returned row, never from raw input.
    """
    if not slug:
        return None
    coll = get_collection(conn, slug)
    if not coll:
        raise LookupError("Collection not found")
    return coll


def register_meme(
    conn: sqlite3.Connection,
    file_path: Path,
    collection_id: str | None = None,
    *,
    source: SourceMeta | None = None,
) -> tuple[Meme, bool]:
    """Hash file, check for duplicate, insert or return existing.

    collection_id is the id of an existing collection (or None). New
    files are probed for width/height/duration. An optional scraped
    source (from a URL upload) is stored alongside. Duplicates are
    returned untouched.

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
    file_meta = probe_file(file_path)
    insert_meme(
        conn,
        new_id,
        h,
        file_size,
        basename,
        ext,
        collection_id=collection_id,
        file_meta=file_meta,
        source=source,
    )
    return get_meme(conn, new_id), False


def get_meme_file_path(
    conn: sqlite3.Connection, meme_id: str, memes_dir: Path
) -> tuple[str | None, Path | None, str | None]:
    """Look up filename and verify file exists on disk.

    Returns (filename, path, error_reason).
    error_reason is None on success, "not_in_db" or "not_on_disk" on failure.
    """
    result = get_meme_filename(conn, meme_id)
    if not result:
        return None, None, MemeError.NOT_IN_DB
    filename, collection = result
    path = meme_file_dir(memes_dir, collection) / filename
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

    result = get_meme_filename(conn, meme_id)
    collection = result[1] if result else None
    file_dir = meme_file_dir(memes_dir, collection)

    new_path = file_dir / new_filename
    if new_path.exists():
        raise FileExistsError("A file with that name already exists")

    (file_dir / filename).rename(new_path)
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
    result = delete_meme_row(conn, meme_id)
    if not result:
        raise LookupError("Not found")
    filename, collection = result
    path = meme_file_dir(memes_dir, collection) / filename
    if path.exists():
        path.unlink()
    delete_thumbnails(meme_id)
    return filename


def move_meme(
    conn: sqlite3.Connection,
    meme_id: str,
    target_collection: str | None,
    memes_dir: Path,
) -> None:
    """Move a meme to a different collection (or to no collection).

    target_collection is a slug (or None).
    Raises LookupError if the meme or the target collection does not exist,
    FileNotFoundError if the meme file is missing on disk.
    """
    result = get_meme_filename(conn, meme_id)
    if not result:
        raise LookupError("Not found")
    filename, current_slug = result

    target = resolve_collection(conn, target_collection)
    target_slug = target["slug"] if target else None
    if current_slug == target_slug:
        return

    src_path = meme_file_dir(memes_dir, current_slug) / filename
    if not src_path.exists():
        raise FileNotFoundError("File not found on disk")

    dst_dir = meme_file_dir(memes_dir, target_slug)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path, new_basename = resolve_unique_path(dst_dir, filename)
    src_path.rename(dst_path)

    if new_basename != filename:
        ext = parse_ext(new_basename)
        update_filename(conn, meme_id, new_basename, ext)
    update_meme_collection(conn, meme_id, target["id"] if target else None)


def create_collection(conn: sqlite3.Connection, name: str, memes_dir: Path) -> dict:
    """Create a new collection. Returns {slug, name}."""
    slug = slugify(name)
    coll_id = str(uuid_mod.uuid4())
    insert_collection(conn, coll_id, slug, name)
    (memes_dir / slug).mkdir(parents=True, exist_ok=True)
    return {"slug": slug, "name": name}


def rename_collection(
    conn: sqlite3.Connection, old_slug: str, new_name: str, memes_dir: Path
) -> dict:
    """Rename a collection. Returns updated {slug, name}.

    Raises LookupError if the collection does not exist, ValueError if the new
    name produces an empty slug, FileExistsError if a stray folder already
    occupies the new slug on disk.
    """
    coll = resolve_collection(conn, old_slug)
    if not coll:
        raise LookupError("Collection not found")
    new_slug = slugify(new_name)
    old_dir = memes_dir / coll["slug"]
    new_dir = memes_dir / new_slug
    if old_slug != new_slug and old_dir.exists() and new_dir.exists():
        raise FileExistsError(f"A folder named '{new_slug}' already exists in the memes dir")
    update_collection(conn, coll["id"], new_slug, new_name)
    if old_dir.exists() and old_slug != new_slug:
        old_dir.rename(new_dir)
    elif not new_dir.exists():
        new_dir.mkdir(parents=True, exist_ok=True)
    return {"slug": new_slug, "name": new_name}


def delete_collection_if_empty(conn: sqlite3.Connection, slug: str, memes_dir: Path) -> None:
    """Delete a collection if it has no memes.

    Raises LookupError if it does not exist, IntegrityError if memes still reference it.
    """
    coll = resolve_collection(conn, slug)
    if not coll:
        raise LookupError("Collection not found")
    delete_collection(conn, coll["id"])
    coll_dir = memes_dir / coll["slug"]
    if coll_dir.exists():
        with contextlib.suppress(OSError):
            coll_dir.rmdir()


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
