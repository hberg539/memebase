import os
import uuid as uuid_mod

from db import find_by_sha256, get_meme, get_meme_filename, insert_meme
from util import file_hash


def resolve_unique_path(directory, basename):
    """Return (dest_path, final_basename) avoiding filename collisions."""
    dest = os.path.join(directory, basename)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(basename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(directory, f"{stem}_{counter}{ext}")
            counter += 1
        basename = os.path.basename(dest)
    return dest, basename


def register_meme(conn, file_path):
    """Hash file, check for duplicate, insert or return existing.

    Returns (meme_dict, is_duplicate).
    """
    h = file_hash(file_path)
    existing_uuid = find_by_sha256(conn, h)
    if existing_uuid:
        os.remove(file_path)
        return get_meme(conn, existing_uuid), True

    new_uuid = str(uuid_mod.uuid4())
    file_size = os.path.getsize(file_path)
    basename = os.path.basename(file_path)
    insert_meme(conn, new_uuid, h, file_size, basename)
    return get_meme(conn, new_uuid), False


def get_meme_file_path(conn, uuid, memes_dir):
    """Look up filename and verify file exists on disk.

    Returns (filename, path, error_reason).
    error_reason is None on success, "not_in_db" or "not_on_disk" on failure.
    """
    filename = get_meme_filename(conn, uuid)
    if not filename:
        return None, None, "not_in_db"
    path = os.path.join(memes_dir, filename)
    if not os.path.exists(path):
        return filename, path, "not_on_disk"
    return filename, path, None
