"""Add source and file metadata columns to memes.

The post-migrate hook backfills width/height/duration for existing memes
by probing the files on disk. Source columns cannot be recovered and are
left NULL.
"""

import sqlite3

from memebase.common import MEMES_DIR
from memebase.log import get_logger
from memebase.probe import probe_file

log = get_logger(__name__)

_BATCH_SIZE = 100

_COLUMNS: dict[str, str] = {
    "source_url": "TEXT",
    "source_site": "TEXT",
    "source_author": "TEXT",
    "source_text": "TEXT",
    "source_date": "TEXT",
    "width": "INTEGER",
    "height": "INTEGER",
    "duration": "REAL",
}


def migrate(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memes)").fetchall()}
    for name, col_type in _COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE memes ADD COLUMN {name} {col_type}")


def post_migrate(conn: sqlite3.Connection) -> None:
    """Probe existing files for width/height/duration where not yet recorded."""
    rows = conn.execute(
        "SELECT id, filename FROM memes WHERE width IS NULL AND height IS NULL"
    ).fetchall()
    if not rows:
        return

    log.info("backfill: probing %d meme(s) for dimensions and duration", len(rows))
    filled = missing = 0
    for i, (meme_id, filename) in enumerate(rows, start=1):
        path = MEMES_DIR / filename
        if not path.is_file():
            missing += 1
            continue
        meta = probe_file(path)
        if meta["width"] is None and meta["height"] is None and meta["duration"] is None:
            continue
        conn.execute(
            "UPDATE memes SET width = ?, height = ?, duration = ? WHERE id = ?",
            (meta["width"], meta["height"], meta["duration"], meme_id),
        )
        filled += 1
        if i % _BATCH_SIZE == 0:
            conn.commit()
            log.info("backfill: %d/%d processed", i, len(rows))
    conn.commit()
    log.info("backfill: done, filled=%d missing_on_disk=%d", filled, missing)
