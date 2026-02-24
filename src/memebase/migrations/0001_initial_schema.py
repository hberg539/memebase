"""Create initial memes and tags tables with indexes."""

import sqlite3


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memes (
            uuid        TEXT PRIMARY KEY,
            sha256      TEXT UNIQUE NOT NULL,
            size        INTEGER NOT NULL DEFAULT 0,
            filename    TEXT NOT NULL,
            ext         TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_ext ON memes(ext)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_created_at ON memes(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_favorite ON memes(favorite)")
