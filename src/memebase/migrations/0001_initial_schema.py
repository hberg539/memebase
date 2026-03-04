"""Create initial memes and tags tables with indexes."""

import sqlite3


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memes (
            id          TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            ext         TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            favorite    INTEGER NOT NULL DEFAULT 0,
            size        INTEGER NOT NULL DEFAULT 0,
            sha256      TEXT UNIQUE NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            meme_id TEXT NOT NULL REFERENCES memes(id) ON DELETE CASCADE,
            tag     TEXT NOT NULL,
            PRIMARY KEY (meme_id, tag)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_ext ON memes(ext)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_created_at ON memes(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_favorite ON memes(favorite)")
