import sqlite3
from unittest.mock import patch

import pytest
from PIL import Image

from memebase.migrate import apply_migrations
from memebase.service import (
    create_collection,
    delete_collection_if_empty,
    delete_meme,
    move_meme,
    register_meme,
    rename_collection,
    rename_meme,
    resolve_unique_path,
)


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


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
    def test_new_file(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "test.png"
        f.write_bytes(b"unique content")
        meme, is_dup = register_meme(conn, f)
        assert not is_dup
        assert meme["filename"] == "test.png"
        assert meme["collection"] is None
        assert f.exists()

    def test_new_file_with_collection(self, tmp_path):
        conn = _make_db()
        conn.execute(
            "INSERT INTO collections (id, slug, name) VALUES ('coll-cats', 'cats', 'Cats')"
        )
        f = tmp_path / "test.png"
        f.write_bytes(b"unique content")
        meme, is_dup = register_meme(conn, f, collection="cats")
        assert not is_dup
        assert meme["collection"] == "cats"

    def test_duplicate_file(self, tmp_path):
        conn = _make_db()
        f1 = tmp_path / "first.png"
        f1.write_bytes(b"same content")
        meme1, is_dup1 = register_meme(conn, f1)
        assert not is_dup1

        f2 = tmp_path / "second.png"
        f2.write_bytes(b"same content")
        meme2, is_dup2 = register_meme(conn, f2)
        assert is_dup2
        assert meme2["id"] == meme1["id"]
        assert f2.exists()

    def test_probes_image_dimensions(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "real.png"
        Image.new("RGB", (320, 200)).save(f)
        meme, _ = register_meme(conn, f)
        assert meme["width"] == 320
        assert meme["height"] == 200
        assert meme["duration"] is None

    def test_stores_source(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "tweet.png"
        f.write_bytes(b"content")
        source = {
            "source_url": "https://x.com/a/status/1",
            "source_site": "twitter",
            "source_author": "a",
            "source_text": "hello",
            "source_date": "2024-01-02 03:04:05",
        }
        meme, _ = register_meme(conn, f, source=source)
        for key, value in source.items():
            assert meme[key] == value

    def test_no_source_leaves_columns_null(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "plain.png"
        f.write_bytes(b"content")
        meme, _ = register_meme(conn, f)
        assert meme["source_url"] is None
        assert meme["source_site"] is None

    def test_duplicate_does_not_attach_source(self, tmp_path):
        conn = _make_db()
        f1 = tmp_path / "first.png"
        f1.write_bytes(b"same")
        register_meme(conn, f1)
        f2 = tmp_path / "second.png"
        f2.write_bytes(b"same")
        source = {
            "source_url": "https://x.com/a/status/1",
            "source_site": "twitter",
            "source_author": "a",
            "source_text": "",
            "source_date": None,
        }
        meme, is_dup = register_meme(conn, f2, source=source)
        assert is_dup
        assert meme["source_url"] is None


class TestRenameMeme:
    def _setup(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "old_name.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        return conn, meme["id"], meme["filename"]

    def test_success(self, tmp_path):
        conn, meme_id, filename = self._setup(tmp_path)
        new = rename_meme(conn, meme_id, filename, "new_name", tmp_path)
        assert new == "new_name.png"
        assert (tmp_path / "new_name.png").exists()
        assert not (tmp_path / "old_name.png").exists()

    def test_collision_raises(self, tmp_path):
        conn, meme_id, filename = self._setup(tmp_path)
        (tmp_path / "taken.png").write_bytes(b"x")
        with pytest.raises(FileExistsError):
            rename_meme(conn, meme_id, filename, "taken", tmp_path)

    def test_unchanged_stem_raises(self, tmp_path):
        conn, meme_id, filename = self._setup(tmp_path)
        with pytest.raises(ValueError, match="unchanged"):
            rename_meme(conn, meme_id, filename, "old_name", tmp_path)

    def test_empty_stem_raises(self, tmp_path):
        conn, meme_id, filename = self._setup(tmp_path)
        with pytest.raises(ValueError, match="empty"):
            rename_meme(conn, meme_id, filename, "   ", tmp_path)


class TestDeleteMeme:
    def _setup(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "doomed.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        return conn, meme["id"]

    @patch("memebase.service.delete_thumbnails")
    def test_removes_row_and_file(self, mock_thumbs, tmp_path):
        conn, meme_id = self._setup(tmp_path)
        assert (tmp_path / "doomed.png").exists()
        filename = delete_meme(conn, meme_id, tmp_path)
        assert filename == "doomed.png"
        assert not (tmp_path / "doomed.png").exists()
        mock_thumbs.assert_called_once_with(meme_id)

    @patch("memebase.service.delete_thumbnails")
    def test_handles_missing_file(self, mock_thumbs, tmp_path):
        conn, meme_id = self._setup(tmp_path)
        (tmp_path / "doomed.png").unlink()
        filename = delete_meme(conn, meme_id, tmp_path)
        assert filename == "doomed.png"
        mock_thumbs.assert_called_once_with(meme_id)

    @patch("memebase.service.delete_thumbnails")
    def test_unknown_id_raises(self, mock_thumbs, tmp_path):
        conn, _ = self._setup(tmp_path)
        with pytest.raises(LookupError):
            delete_meme(conn, "nonexistent-id", tmp_path)

    @patch("memebase.service.delete_thumbnails")
    def test_delete_in_collection(self, mock_thumbs, tmp_path):
        conn = _make_db()
        conn.execute(
            "INSERT INTO collections (id, slug, name) VALUES ('coll-cats', 'cats', 'Cats')"
        )
        coll_dir = tmp_path / "cats"
        coll_dir.mkdir()
        f = coll_dir / "cat.png"
        f.write_bytes(b"meow")
        meme, _ = register_meme(conn, f, collection="cats")
        filename = delete_meme(conn, meme["id"], tmp_path)
        assert filename == "cat.png"
        assert not f.exists()


class TestMoveMeme:
    def test_move_to_collection(self, tmp_path):
        conn = _make_db()
        conn.execute(
            "INSERT INTO collections (id, slug, name) VALUES ('coll-cats', 'cats', 'Cats')"
        )
        f = tmp_path / "meme.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        move_meme(conn, meme["id"], "cats", tmp_path)
        assert (tmp_path / "cats" / "meme.png").exists()
        assert not (tmp_path / "meme.png").exists()
        row = conn.execute("SELECT collection_id FROM memes WHERE id = ?", (meme["id"],)).fetchone()
        assert row["collection_id"] == "coll-cats"

    def test_move_to_none(self, tmp_path):
        conn = _make_db()
        conn.execute(
            "INSERT INTO collections (id, slug, name) VALUES ('coll-cats', 'cats', 'Cats')"
        )
        coll_dir = tmp_path / "cats"
        coll_dir.mkdir()
        f = coll_dir / "meme.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f, collection="cats")
        move_meme(conn, meme["id"], None, tmp_path)
        assert (tmp_path / "meme.png").exists()
        assert not (coll_dir / "meme.png").exists()
        row = conn.execute("SELECT collection_id FROM memes WHERE id = ?", (meme["id"],)).fetchone()
        assert row["collection_id"] is None

    def test_noop_same_collection(self, tmp_path):
        conn = _make_db()
        f = tmp_path / "meme.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        move_meme(conn, meme["id"], None, tmp_path)
        assert (tmp_path / "meme.png").exists()

    def test_filename_collision(self, tmp_path):
        conn = _make_db()
        conn.execute(
            "INSERT INTO collections (id, slug, name) VALUES ('coll-cats', 'cats', 'Cats')"
        )
        coll_dir = tmp_path / "cats"
        coll_dir.mkdir()
        (coll_dir / "meme.png").write_bytes(b"existing")
        f = tmp_path / "meme.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f)
        move_meme(conn, meme["id"], "cats", tmp_path)
        assert (coll_dir / "meme_1.png").exists()
        row = conn.execute("SELECT filename FROM memes WHERE id = ?", (meme["id"],)).fetchone()
        assert row["filename"] == "meme_1.png"


class TestCreateCollection:
    def test_creates_collection(self, tmp_path):
        conn = _make_db()
        result = create_collection(conn, "My Cats", tmp_path)
        assert result["slug"] == "my-cats"
        assert result["name"] == "My Cats"
        assert (tmp_path / "my-cats").is_dir()

    def test_duplicate_raises(self, tmp_path):
        conn = _make_db()
        create_collection(conn, "Cats", tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            create_collection(conn, "Cats", tmp_path)


class TestRenameCollection:
    def test_renames_collection(self, tmp_path):
        conn = _make_db()
        create_collection(conn, "Cats", tmp_path)
        result = rename_collection(conn, "cats", "Dogs", tmp_path)
        assert result["slug"] == "dogs"
        assert result["name"] == "Dogs"
        assert (tmp_path / "dogs").is_dir()
        assert not (tmp_path / "cats").exists()

    def test_rename_preserves_meme_association(self, tmp_path):
        conn = _make_db()
        create_collection(conn, "Cats", tmp_path)
        coll_dir = tmp_path / "cats"
        f = coll_dir / "meme.png"
        f.write_bytes(b"data")
        meme, _ = register_meme(conn, f, collection="cats")
        rename_collection(conn, "cats", "Dogs", tmp_path)
        from memebase.db import get_meme as db_get_meme

        updated = db_get_meme(conn, meme["id"])
        assert updated["collection"] == "dogs"


class TestDeleteCollection:
    def test_deletes_empty(self, tmp_path):
        conn = _make_db()
        create_collection(conn, "Cats", tmp_path)
        delete_collection_if_empty(conn, "cats", tmp_path)
        assert not (tmp_path / "cats").exists()
        row = conn.execute("SELECT * FROM collections WHERE slug = 'cats'").fetchone()
        assert row is None

    def test_blocks_nonempty(self, tmp_path):
        conn = _make_db()
        create_collection(conn, "Cats", tmp_path)
        coll_dir = tmp_path / "cats"
        f = coll_dir / "meme.png"
        f.write_bytes(b"data")
        register_meme(conn, f, collection="cats")
        with pytest.raises(sqlite3.IntegrityError):
            delete_collection_if_empty(conn, "cats", tmp_path)
