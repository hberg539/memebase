"""Add collections table and memes.collection foreign key."""

import sqlite3


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("""
        ALTER TABLE memes ADD COLUMN collection_id TEXT
            REFERENCES collections(id) ON DELETE RESTRICT
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_collection_id ON memes(collection_id)")
