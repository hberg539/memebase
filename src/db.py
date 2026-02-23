import sqlite3

from common import DB_PATH, MEMES_DIR, SORT_OPTIONS

import os


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(MEMES_DIR, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memes (
                uuid        TEXT PRIMARY KEY,
                sha256      TEXT UNIQUE NOT NULL,
                size        INTEGER NOT NULL DEFAULT 0,
                filename    TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                copy_count  INTEGER NOT NULL DEFAULT 0,
                favorite    INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                uuid TEXT NOT NULL REFERENCES memes(uuid) ON DELETE CASCADE,
                tag  TEXT NOT NULL,
                PRIMARY KEY (uuid, tag)
            )
        """)


# ---------------------------------------------------------------------------
# Single meme operations
# ---------------------------------------------------------------------------


def get_meme(conn, uuid):
    """Get a meme dict with tags by uuid, or None if not found."""
    row = conn.execute(
        "SELECT uuid, sha256, size, filename, description, copy_count, favorite, created_at "
        "FROM memes WHERE uuid = ?",
        (uuid,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    tags = conn.execute("SELECT tag FROM tags WHERE uuid = ? ORDER BY tag", (uuid,)).fetchall()
    d["tags"] = [t["tag"] for t in tags]
    return d


def get_meme_filename(conn, uuid):
    """Get just the filename for a meme, or None if not found."""
    row = conn.execute("SELECT filename FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    return row["filename"] if row else None


def get_meme_for_serving(conn, uuid):
    """Get (filename, sha256) for serving a meme file, or None if not found."""
    row = conn.execute("SELECT filename, sha256 FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    return (row["filename"], row["sha256"]) if row else None


def find_by_sha256(conn, sha256):
    """Find a meme uuid by its sha256 hash. Returns uuid string or None."""
    row = conn.execute("SELECT uuid FROM memes WHERE sha256 = ?", (sha256,)).fetchone()
    return row["uuid"] if row else None


def insert_meme(conn, uuid, sha256, size, filename):
    """Insert a new meme row."""
    conn.execute(
        "INSERT INTO memes (uuid, sha256, size, filename) VALUES (?, ?, ?, ?)",
        (uuid, sha256, size, filename),
    )


def update_favorite(conn, uuid, favorite):
    """Set the favorite flag (0 or 1)."""
    conn.execute(
        "UPDATE memes SET favorite = ?, updated_at = datetime('now') WHERE uuid = ?",
        (1 if favorite else 0, uuid),
    )


def update_description(conn, uuid, description):
    """Update the description text."""
    conn.execute(
        "UPDATE memes SET description = ?, updated_at = datetime('now') WHERE uuid = ?",
        (description, uuid),
    )


def update_filename(conn, uuid, filename):
    """Update the stored filename."""
    conn.execute(
        "UPDATE memes SET filename = ?, updated_at = datetime('now') WHERE uuid = ?",
        (filename, uuid),
    )


def increment_copy_count(conn, uuid):
    """Increment copy_count and return the new value, or None if not found."""
    row = conn.execute("SELECT uuid FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    if not row:
        return None
    conn.execute("UPDATE memes SET copy_count = copy_count + 1 WHERE uuid = ?", (uuid,))
    updated = conn.execute("SELECT copy_count FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    return updated["copy_count"]


def delete_meme_row(conn, uuid):
    """Delete a meme row, returning the filename (for file cleanup), or None if not found."""
    row = conn.execute("SELECT filename FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    if not row:
        return None
    conn.execute("DELETE FROM memes WHERE uuid = ?", (uuid,))
    return row["filename"]


# ---------------------------------------------------------------------------
# Tag operations
# ---------------------------------------------------------------------------


def get_all_tags(conn):
    """Return a sorted list of all distinct tag strings."""
    rows = conn.execute("SELECT DISTINCT tag FROM tags ORDER BY tag").fetchall()
    return [r["tag"] for r in rows]


def _normalize_tags(tags):
    """Deduplicate and normalize a list of tags."""
    return {t.strip().lower() for t in set(tags)} - {""}


def set_tags(conn, uuid, tags):
    """Replace all tags for a meme."""
    conn.execute("DELETE FROM tags WHERE uuid = ?", (uuid,))
    for tag in _normalize_tags(tags):
        conn.execute("INSERT INTO tags (uuid, tag) VALUES (?, ?)", (uuid, tag))


def add_tags(conn, uuid, tags):
    """Add tags to a meme (ignores duplicates)."""
    for tag in _normalize_tags(tags):
        conn.execute("INSERT OR IGNORE INTO tags (uuid, tag) VALUES (?, ?)", (uuid, tag))


def remove_tags(conn, uuid, tags):
    """Remove specific tags from a meme."""
    for tag in _normalize_tags(tags):
        conn.execute("DELETE FROM tags WHERE uuid = ? AND tag = ?", (uuid, tag))


# ---------------------------------------------------------------------------
# Faceted query
# ---------------------------------------------------------------------------


def _build_where(parts):
    return (" WHERE " + " AND ".join(parts)) if parts else ""


def query_memes(
    conn,
    q="",
    page=1,
    page_size=50,
    ext_filter=None,
    tag_filters=None,
    fav_filter=False,
    sort="",
):
    """
    Run a faceted meme query. Returns dict with keys:
      memes    — list of meme dicts (with tags)
      total    — total matching count
      filters  — {exts: {ext: count}, tags: {tag: count}, fav_count: int}
    """
    tag_filters = tag_filters or []
    order = SORT_OPTIONS.get(sort, "m.created_at DESC")

    # Build individual filter clauses
    search_parts, search_params = [], []
    if q:
        for w in q.split():
            like = f"%{w}%"
            search_parts.append(
                "(m.filename LIKE ? OR m.description LIKE ? "
                "OR EXISTS (SELECT 1 FROM tags ts WHERE ts.uuid = m.uuid AND ts.tag LIKE ?))"
            )
            search_params.extend([like, like, like])

    ext_parts = ["LOWER(m.filename) LIKE ?"] if ext_filter else []
    ext_params = [f"%.{ext_filter}"] if ext_filter else []

    tag_parts, tag_params = [], []
    for tf in tag_filters:
        tag_parts.append("EXISTS (SELECT 1 FROM tags tf WHERE tf.uuid = m.uuid AND tf.tag = ?)")
        tag_params.append(tf)

    fav_parts = ["m.favorite = 1"] if fav_filter else []

    # Full filter for results + total count
    all_parts = search_parts + ext_parts + tag_parts + fav_parts
    all_params = search_params + ext_params + tag_params
    where_sql = _build_where(all_parts)

    total = conn.execute(f"SELECT COUNT(*) as c FROM memes m{where_sql}", all_params).fetchone()[
        "c"
    ]

    # Base set from search only — for the full list of available exts/tags
    base_where = _build_where(search_parts)

    all_exts_rows = conn.execute(
        f"""SELECT REPLACE(LOWER(SUBSTR(m.filename, INSTR(m.filename, '.'))), '.', '') as ext,
                   COUNT(*) as c
            FROM memes m{base_where}
            GROUP BY ext ORDER BY ext""",
        search_params,
    ).fetchall()
    all_exts = {r["ext"]: r["c"] for r in all_exts_rows if r["ext"]}

    all_tags_rows = conn.execute(
        f"""SELECT t.tag, COUNT(DISTINCT m.uuid) as c
            FROM memes m JOIN tags t ON m.uuid = t.uuid
            {_build_where(["1=1"] + search_parts)}
            GROUP BY t.tag ORDER BY t.tag""",
        search_params,
    ).fetchall()
    all_tags = {r["tag"]: r["c"] for r in all_tags_rows}

    # Faceted counts: each dimension excludes itself, includes all others
    # Ext counts (search + tag + fav, but NOT ext)
    ext_facet_parts = search_parts + tag_parts + fav_parts
    ext_facet_params = search_params + tag_params
    ext_facet_where = _build_where(ext_facet_parts)
    ext_rows = conn.execute(
        f"""SELECT REPLACE(LOWER(SUBSTR(m.filename, INSTR(m.filename, '.'))), '.', '') as ext,
                   COUNT(*) as c
            FROM memes m{ext_facet_where}
            GROUP BY ext""",
        ext_facet_params,
    ).fetchall()
    ext_counts = {r["ext"]: r["c"] for r in ext_rows if r["ext"]}
    exts = {e: ext_counts.get(e, 0) for e in all_exts}

    # Tag counts (search + ext + fav + active tags)
    tag_facet_parts = search_parts + ext_parts + tag_parts + fav_parts
    tag_facet_params = search_params + ext_params + tag_params
    tag_facet_where = _build_where(["1=1"] + tag_facet_parts)
    tag_rows = conn.execute(
        f"""SELECT t.tag, COUNT(DISTINCT m.uuid) as c
            FROM memes m JOIN tags t ON m.uuid = t.uuid
            {tag_facet_where}
            GROUP BY t.tag""",
        tag_facet_params,
    ).fetchall()
    tag_counts = {r["tag"]: r["c"] for r in tag_rows}
    tags = {t: tag_counts.get(t, 0) for t in all_tags}

    # Fav count (search + ext + tag, but NOT fav)
    fav_facet_parts = search_parts + ext_parts + tag_parts + ["m.favorite = 1"]
    fav_facet_params = search_params + ext_params + tag_params
    fav_facet_where = _build_where(fav_facet_parts)
    fav_count = conn.execute(
        f"SELECT COUNT(*) as c FROM memes m{fav_facet_where}",
        fav_facet_params,
    ).fetchone()["c"]

    # Fetch one page of memes
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT m.uuid FROM memes m{where_sql} ORDER BY {order} LIMIT ? OFFSET ?",
        all_params + [page_size, offset],
    ).fetchall()

    memes = [get_meme(conn, row["uuid"]) for row in rows]

    return {
        "memes": memes,
        "total": total,
        "filters": {
            "exts": exts,
            "tags": tags,
            "fav_count": fav_count,
        },
    }
