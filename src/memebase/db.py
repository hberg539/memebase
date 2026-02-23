import sqlite3
from typing import Any

from flask import Flask, g

from memebase.common import DB_PATH, MEMES_DIR, SORT_OPTIONS, THUMBNAILS_DIR
from memebase.schemas import Meme
from memebase.util import normalize_tags


def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> sqlite3.Connection:
    """Return the per-request database connection, creating it on first call."""
    if "db" not in g:
        g.db = _connect_db()
    return g.db


def _close_db(exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app: Flask) -> None:
    """Register the database teardown hook on the Flask app."""
    app.teardown_appcontext(_close_db)


def init_db() -> None:
    MEMES_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    with _connect_db() as conn:
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_created_at ON memes(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_favorite ON memes(favorite)")


# ---------------------------------------------------------------------------
# Single meme operations
# ---------------------------------------------------------------------------


def get_meme(conn: sqlite3.Connection, uuid: str) -> Meme | None:
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


def get_meme_filename(conn: sqlite3.Connection, uuid: str) -> str | None:
    """Get just the filename for a meme, or None if not found."""
    row = conn.execute("SELECT filename FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    return row["filename"] if row else None


def get_meme_for_serving(conn: sqlite3.Connection, uuid: str) -> tuple[str, str] | None:
    """Get (filename, sha256) for serving a meme file, or None if not found."""
    row = conn.execute("SELECT filename, sha256 FROM memes WHERE uuid = ?", (uuid,)).fetchone()
    return (row["filename"], row["sha256"]) if row else None


def find_by_sha256(conn: sqlite3.Connection, sha256: str) -> str | None:
    """Find a meme uuid by its sha256 hash. Returns uuid string or None."""
    row = conn.execute("SELECT uuid FROM memes WHERE sha256 = ?", (sha256,)).fetchone()
    return row["uuid"] if row else None


def insert_meme(conn: sqlite3.Connection, uuid: str, sha256: str, size: int, filename: str) -> None:
    """Insert a new meme row."""
    conn.execute(
        "INSERT INTO memes (uuid, sha256, size, filename) VALUES (?, ?, ?, ?)",
        (uuid, sha256, size, filename),
    )


def update_favorite(conn: sqlite3.Connection, uuid: str, favorite: bool) -> None:
    """Set the favorite flag (0 or 1)."""
    conn.execute(
        "UPDATE memes SET favorite = ?, updated_at = datetime('now') WHERE uuid = ?",
        (1 if favorite else 0, uuid),
    )


def update_description(conn: sqlite3.Connection, uuid: str, description: str) -> None:
    """Update the description text."""
    conn.execute(
        "UPDATE memes SET description = ?, updated_at = datetime('now') WHERE uuid = ?",
        (description, uuid),
    )


def update_filename(conn: sqlite3.Connection, uuid: str, filename: str) -> None:
    """Update the stored filename."""
    conn.execute(
        "UPDATE memes SET filename = ?, updated_at = datetime('now') WHERE uuid = ?",
        (filename, uuid),
    )


def increment_copy_count(conn: sqlite3.Connection, uuid: str) -> int | None:
    """Increment copy_count and return the new value, or None if not found."""
    row = conn.execute(
        "UPDATE memes SET copy_count = copy_count + 1 WHERE uuid = ? RETURNING copy_count",
        (uuid,),
    ).fetchone()
    return row["copy_count"] if row else None


def delete_meme_row(conn: sqlite3.Connection, uuid: str) -> str | None:
    """Delete a meme row, returning the filename (for file cleanup), or None if not found."""
    row = conn.execute(
        "DELETE FROM memes WHERE uuid = ? RETURNING filename",
        (uuid,),
    ).fetchone()
    return row["filename"] if row else None


# ---------------------------------------------------------------------------
# Tag operations
# ---------------------------------------------------------------------------


def get_all_tags(conn: sqlite3.Connection) -> list[str]:
    """Return a sorted list of all distinct tag strings."""
    rows = conn.execute("SELECT DISTINCT tag FROM tags ORDER BY tag").fetchall()
    return [r["tag"] for r in rows]


def set_tags(conn: sqlite3.Connection, uuid: str, tags: list[str]) -> None:
    """Replace all tags for a meme."""
    conn.execute("DELETE FROM tags WHERE uuid = ?", (uuid,))
    normalized = normalize_tags(tags)
    if normalized:
        conn.executemany(
            "INSERT INTO tags (uuid, tag) VALUES (?, ?)",
            [(uuid, tag) for tag in normalized],
        )


def add_tags(conn: sqlite3.Connection, uuid: str, tags: list[str]) -> None:
    """Add tags to a meme (ignores duplicates)."""
    normalized = normalize_tags(tags)
    if normalized:
        conn.executemany(
            "INSERT OR IGNORE INTO tags (uuid, tag) VALUES (?, ?)",
            [(uuid, tag) for tag in normalized],
        )


def remove_tags(conn: sqlite3.Connection, uuid: str, tags: list[str]) -> None:
    """Remove specific tags from a meme."""
    normalized = normalize_tags(tags)
    if normalized:
        conn.executemany(
            "DELETE FROM tags WHERE uuid = ? AND tag = ?",
            [(uuid, tag) for tag in normalized],
        )


# ---------------------------------------------------------------------------
# Faceted query
# ---------------------------------------------------------------------------


def _build_where(parts: list[str]) -> str:
    return (" WHERE " + " AND ".join(parts)) if parts else ""


def _build_filter_clauses(
    q: str,
    ext_filter: str | None,
    tag_filters: list[str],
    fav_filter: bool,
) -> dict[str, tuple[list[str], list[str]]]:
    """Build SQL WHERE clause parts and params for each filter dimension.

    Returns dict with keys: search, ext, tag, fav.
    Each value is (parts, params).
    """
    search_parts: list[str] = []
    search_params: list[str] = []
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

    tag_parts: list[str] = []
    tag_params: list[str] = []
    for tf in tag_filters:
        tag_parts.append("EXISTS (SELECT 1 FROM tags tf WHERE tf.uuid = m.uuid AND tf.tag = ?)")
        tag_params.append(tf)

    fav_parts = ["m.favorite = 1"] if fav_filter else []

    return {
        "search": (search_parts, search_params),
        "ext": (ext_parts, ext_params),
        "tag": (tag_parts, tag_params),
        "fav": (fav_parts, []),
    }


def _get_facet_counts(
    conn: sqlite3.Connection,
    clauses: dict[str, tuple[list[str], list[str]]],
) -> dict[str, Any]:
    """Run faceted count queries for ext, tag, and fav dimensions.

    Returns {"exts": {...}, "tags": {...}, "fav_count": int}.
    """
    search_parts, search_params = clauses["search"]
    ext_parts, ext_params = clauses["ext"]
    tag_parts, tag_params = clauses["tag"]
    fav_parts, _ = clauses["fav"]

    # Base set from search only - for the full list of available exts/tags
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
            {_build_where(["1=1", *search_parts])}
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
    tag_facet_where = _build_where(["1=1", *tag_facet_parts])
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

    return {"exts": exts, "tags": tags, "fav_count": fav_count}


def query_memes(
    conn: sqlite3.Connection,
    q: str = "",
    page: int = 1,
    page_size: int = 50,
    ext_filter: str | None = None,
    tag_filters: list[str] | None = None,
    fav_filter: bool = False,
    sort: str = "",
) -> dict[str, Any]:
    """Run a faceted meme query.

    Returns dict with keys:
      memes   - list of meme dicts (with tags)
      total   - total matching count
      filters - {exts: {ext: count}, tags: {tag: count}, fav_count: int}
    """
    clauses = _build_filter_clauses(q, ext_filter, tag_filters or [], fav_filter)
    order = SORT_OPTIONS.get(sort, "m.created_at DESC")

    # Combine all clause parts for the full filter
    all_parts = [p for key in ("search", "ext", "tag", "fav") for p in clauses[key][0]]
    all_params = [p for key in ("search", "ext", "tag") for p in clauses[key][1]]
    where_sql = _build_where(all_parts)

    total = conn.execute(f"SELECT COUNT(*) as c FROM memes m{where_sql}", all_params).fetchone()[
        "c"
    ]

    filters = _get_facet_counts(conn, clauses)

    # Fetch one page of memes with all columns
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT m.uuid, m.sha256, m.size, m.filename, m.description, "
        f"m.copy_count, m.favorite, m.created_at "
        f"FROM memes m{where_sql} ORDER BY {order} LIMIT ? OFFSET ?",
        [*all_params, page_size, offset],
    ).fetchall()

    if not rows:
        return {"memes": [], "total": total, "filters": filters}

    # Batch-fetch tags for all memes in a single query
    uuids = [row["uuid"] for row in rows]
    placeholders = ",".join("?" * len(uuids))
    tag_rows = conn.execute(
        f"SELECT uuid, tag FROM tags WHERE uuid IN ({placeholders}) ORDER BY tag",
        uuids,
    ).fetchall()

    tags_by_uuid: dict[str, list[str]] = {u: [] for u in uuids}
    for tr in tag_rows:
        tags_by_uuid[tr["uuid"]].append(tr["tag"])

    memes: list[Meme] = []
    for row in rows:
        meme: Meme = {**dict(row), "tags": tags_by_uuid[row["uuid"]]}
        memes.append(meme)

    return {"memes": memes, "total": total, "filters": filters}
