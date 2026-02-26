import sqlite3
from unittest.mock import patch

import pytest

from memebase.migrate import apply_migrations
from memebase.service import delete_meme, register_meme, rename_meme, resolve_unique_path


class TestResolveUniquePath:
    def test_no_collision(self, tmp_path):
        dest, basename = resolve_unique_path(tmp_path, "hello.png")
        assert basename == "hello.png"
        assert dest == tmp_path / "hello.png"

    def test_single_collision(self, tmp_path):
        (tmp_path / "hello.png").write_bytes(b"x")
        dest, basename = resolve_unique_path(tmp_path, "hello.png")
        assert basename == "hello_1.png"
        assert dest == tmp_path / "hello_1.png"

    def test_multiple_collisions(self, tmp_path):
        (tmp_path / "hello.png").write_bytes(b"x")
        (tmp_path / "hello_1.png").write_bytes(b"x")
        (tmp_path / "hello_2.png").write_bytes(b"x")
        _dest, basename = resolve_unique_path(tmp_path, "hello.png")
        assert basename == "hello_3.png"


class TestRegisterMeme:
    def _make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        apply_migrations(conn)
        return conn

    def test_new_file(self, tmp_path):
        conn = self._make_db()
        f = tmp_path / "test.png"
        f.write_bytes(b"unique content")
        meme, is_dup = register_meme(conn, f)
        assert not is_dup
        assert meme["filename"] == "test.png"
        assert f.exists()  # new files stay on disk

    def test_duplicate_file(self, tmp_path):
        conn = self._make_db()
        # Insert first file
        f1 = tmp_path / "first.png"
        f1.write_bytes(b"same content")
        meme1, is_dup1 = register_meme(conn, f1)
        assert not is_dup1

        # Insert duplicate
        f2 = tmp_path / "second.png"
        f2.write_bytes(b"same content")
        meme2, is_dup2 = register_meme(conn, f2)
        assert is_dup2
        assert meme2["uuid"] == meme1["uuid"]
        assert f2.exists()


class TestRenameMeme:
    def _setup(self, tmp_path):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        apply_migrations(conn)
        f = tmp_path / "old_name.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        return conn, meme["uuid"], meme["filename"]

    def test_success(self, tmp_path):
        conn, uuid, filename = self._setup(tmp_path)
        new = rename_meme(conn, uuid, filename, "new_name", tmp_path)
        assert new == "new_name.png"
        assert (tmp_path / "new_name.png").exists()
        assert not (tmp_path / "old_name.png").exists()

    def test_collision_raises(self, tmp_path):
        conn, uuid, filename = self._setup(tmp_path)
        (tmp_path / "taken.png").write_bytes(b"x")
        with pytest.raises(FileExistsError):
            rename_meme(conn, uuid, filename, "taken", tmp_path)

    def test_unchanged_stem_raises(self, tmp_path):
        conn, uuid, filename = self._setup(tmp_path)
        with pytest.raises(ValueError, match="unchanged"):
            rename_meme(conn, uuid, filename, "old_name", tmp_path)

    def test_empty_stem_raises(self, tmp_path):
        conn, uuid, filename = self._setup(tmp_path)
        with pytest.raises(ValueError, match="empty"):
            rename_meme(conn, uuid, filename, "   ", tmp_path)


class TestDeleteMeme:
    def _setup(self, tmp_path):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        apply_migrations(conn)
        f = tmp_path / "doomed.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        return conn, meme["uuid"]

    @patch("memebase.service.delete_thumbnails")
    def test_removes_row_and_file(self, mock_thumbs, tmp_path):
        conn, uuid = self._setup(tmp_path)
        assert (tmp_path / "doomed.png").exists()
        filename = delete_meme(conn, uuid, tmp_path)
        assert filename == "doomed.png"
        assert not (tmp_path / "doomed.png").exists()
        mock_thumbs.assert_called_once_with(uuid)

    @patch("memebase.service.delete_thumbnails")
    def test_handles_missing_file(self, mock_thumbs, tmp_path):
        conn, uuid = self._setup(tmp_path)
        (tmp_path / "doomed.png").unlink()
        filename = delete_meme(conn, uuid, tmp_path)
        assert filename == "doomed.png"
        mock_thumbs.assert_called_once_with(uuid)

    @patch("memebase.service.delete_thumbnails")
    def test_unknown_uuid_raises(self, mock_thumbs, tmp_path):
        conn, _ = self._setup(tmp_path)
        with pytest.raises(LookupError):
            delete_meme(conn, "nonexistent-uuid", tmp_path)
