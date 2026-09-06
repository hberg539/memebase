"""Add source and file metadata columns to memes."""

import sqlite3

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
