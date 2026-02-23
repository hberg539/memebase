import os
import sqlite3

from memebase.service import resolve_unique_path, register_meme


class TestResolveUniquePath:
    def test_no_collision(self, tmp_path):
        dest, basename = resolve_unique_path(str(tmp_path), "hello.png")
        assert basename == "hello.png"
        assert dest == os.path.join(str(tmp_path), "hello.png")

    def test_single_collision(self, tmp_path):
        (tmp_path / "hello.png").write_bytes(b"x")
        dest, basename = resolve_unique_path(str(tmp_path), "hello.png")
        assert basename == "hello_1.png"
        assert dest == os.path.join(str(tmp_path), "hello_1.png")

    def test_multiple_collisions(self, tmp_path):
        (tmp_path / "hello.png").write_bytes(b"x")
        (tmp_path / "hello_1.png").write_bytes(b"x")
        (tmp_path / "hello_2.png").write_bytes(b"x")
        dest, basename = resolve_unique_path(str(tmp_path), "hello.png")
        assert basename == "hello_3.png"


class TestRegisterMeme:
    def _make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            CREATE TABLE memes (
                uuid TEXT PRIMARY KEY,
                sha256 TEXT UNIQUE NOT NULL,
                size INTEGER NOT NULL DEFAULT 0,
                filename TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                copy_count INTEGER NOT NULL DEFAULT 0,
                favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE tags (
                uuid TEXT NOT NULL REFERENCES memes(uuid) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                PRIMARY KEY (uuid, tag)
            )
        """)
        return conn

    def test_new_file(self, tmp_path):
        conn = self._make_db()
        f = tmp_path / "test.png"
        f.write_bytes(b"unique content")
        meme, is_dup = register_meme(conn, str(f))
        assert not is_dup
        assert meme["filename"] == "test.png"
        assert f.exists()  # new files stay on disk

    def test_duplicate_file(self, tmp_path):
        conn = self._make_db()
        # Insert first file
        f1 = tmp_path / "first.png"
        f1.write_bytes(b"same content")
        meme1, is_dup1 = register_meme(conn, str(f1))
        assert not is_dup1

        # Insert duplicate
        f2 = tmp_path / "second.png"
        f2.write_bytes(b"same content")
        meme2, is_dup2 = register_meme(conn, str(f2))
        assert is_dup2
        assert meme2["uuid"] == meme1["uuid"]
        assert f2.exists()
