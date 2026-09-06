import importlib
import sqlite3
import types
from unittest.mock import patch

from PIL import Image

from memebase.migrate import apply_migrations, get_version, set_version

_initial = importlib.import_module("memebase.migrations.0001_initial_schema")
_metadata = importlib.import_module("memebase.migrations.0002_metadata")


class TestGetSetVersion:
    def test_fresh_db_version_is_zero(self):
        conn = sqlite3.connect(":memory:")
        assert get_version(conn) == 0

    def test_set_and_get_version(self):
        conn = sqlite3.connect(":memory:")
        set_version(conn, 5)
        assert get_version(conn) == 5


class TestApplyMigrations:
    def test_fresh_database(self):
        """Fresh DB gets all migrations applied and correct version."""
        conn = sqlite3.connect(":memory:")
        apply_migrations(conn)
        assert get_version(conn) == 2
        # Verify tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [r[0] for r in tables]
        assert "memes" in table_names
        assert "tags" in table_names

    def test_already_migrated_database(self):
        """DB already at latest version has no migrations applied."""
        conn = sqlite3.connect(":memory:")
        apply_migrations(conn)
        assert get_version(conn) == 2
        # Running again should be a no-op
        apply_migrations(conn)
        assert get_version(conn) == 2

    def test_metadata_columns_added(self):
        """Migration 0002 adds source and file metadata columns."""
        conn = sqlite3.connect(":memory:")
        apply_migrations(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(memes)").fetchall()}
        expected = {
            "source_url",
            "source_site",
            "source_author",
            "source_text",
            "source_date",
            "width",
            "height",
            "duration",
        }
        assert expected <= cols

    def test_metadata_migration_upgrades_v1_database(self):
        """A database at version 1 with existing rows migrates without losing data."""
        conn = sqlite3.connect(":memory:")
        _initial.migrate(conn)
        set_version(conn, 1)
        conn.execute(
            "INSERT INTO memes (id, sha256, size, filename, ext) VALUES (?, ?, ?, ?, ?)",
            ("old-id", "hash", 1, "old.png", "png"),
        )
        apply_migrations(conn)
        assert get_version(conn) == 2
        row = conn.execute(
            "SELECT filename, source_url, width FROM memes WHERE id = 'old-id'"
        ).fetchone()
        assert row == ("old.png", None, None)

    def test_metadata_migration_is_idempotent(self):
        """Running migration 0002 twice does not fail on existing columns."""
        conn = sqlite3.connect(":memory:")
        apply_migrations(conn)
        _metadata.migrate(conn)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(memes)").fetchall()]
        assert cols.count("source_url") == 1


class TestPostMigrateHook:
    def _fake_module(self, name, hook=None):
        mod = types.ModuleType(name)
        mod.migrate = lambda conn: conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
        if hook is not None:
            mod.post_migrate = hook
        return mod

    def test_hook_runs_after_schema_and_version_bump(self):
        seen = {}

        def hook(conn):
            seen["version"] = get_version(conn)
            conn.execute("INSERT INTO t (x) VALUES (1)")

        conn = sqlite3.connect(":memory:")
        mod = self._fake_module("fake_0009", hook)
        with patch("memebase.migrate._discover_migrations", return_value=[(9, mod)]):
            apply_migrations(conn)
        assert seen["version"] == 9
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1

    def test_module_without_hook_is_fine(self):
        conn = sqlite3.connect(":memory:")
        mod = self._fake_module("fake_0009")
        with patch("memebase.migrate._discover_migrations", return_value=[(9, mod)]):
            apply_migrations(conn)
        assert get_version(conn) == 9

    def test_failing_hook_does_not_block_startup(self):
        def hook(conn):
            conn.execute("INSERT INTO t (x) VALUES (1)")
            raise RuntimeError("boom")

        conn = sqlite3.connect(":memory:")
        mod = self._fake_module("fake_0009", hook)
        with patch("memebase.migrate._discover_migrations", return_value=[(9, mod)]):
            apply_migrations(conn)  # must not raise
        assert get_version(conn) == 9
        # partial hook work was rolled back
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0

    def test_hook_only_runs_when_migration_is_applied(self):
        calls = []
        conn = sqlite3.connect(":memory:")
        mod = self._fake_module("fake_0009", lambda conn: calls.append(1))
        with patch("memebase.migrate._discover_migrations", return_value=[(9, mod)]):
            apply_migrations(conn)
        with patch("memebase.migrate._discover_migrations", return_value=[]):
            apply_migrations(conn)
        assert calls == [1]


class TestMetadataBackfill:
    def _v1_db_with_meme(self, filename):
        conn = sqlite3.connect(":memory:")
        _initial.migrate(conn)
        set_version(conn, 1)
        conn.execute(
            "INSERT INTO memes (id, sha256, size, filename, ext) VALUES (?, ?, ?, ?, ?)",
            ("m1", f"hash-{filename}", 1, filename, filename.rsplit(".", 1)[-1]),
        )
        conn.commit()
        return conn

    def test_backfills_dimensions_from_disk(self, tmp_path):
        Image.new("RGB", (64, 32)).save(tmp_path / "old.png")
        conn = self._v1_db_with_meme("old.png")
        with patch.object(_metadata, "MEMES_DIR", tmp_path):
            apply_migrations(conn)
        row = conn.execute("SELECT width, height, duration FROM memes WHERE id = 'm1'").fetchone()
        assert row == (64, 32, None)

    def test_missing_file_is_skipped(self, tmp_path):
        conn = self._v1_db_with_meme("gone.png")
        with patch.object(_metadata, "MEMES_DIR", tmp_path):
            apply_migrations(conn)
        row = conn.execute("SELECT width, height FROM memes WHERE id = 'm1'").fetchone()
        assert row == (None, None)
        assert get_version(conn) == 2

    def test_already_filled_rows_are_left_alone(self, tmp_path):
        Image.new("RGB", (64, 32)).save(tmp_path / "old.png")
        conn = self._v1_db_with_meme("old.png")
        _metadata.migrate(conn)
        conn.execute("UPDATE memes SET width = 1, height = 1 WHERE id = 'm1'")
        with patch.object(_metadata, "MEMES_DIR", tmp_path):
            _metadata.post_migrate(conn)
        row = conn.execute("SELECT width, height FROM memes WHERE id = 'm1'").fetchone()
        assert row == (1, 1)

    def test_source_columns_stay_null(self, tmp_path):
        Image.new("RGB", (8, 8)).save(tmp_path / "old.png")
        conn = self._v1_db_with_meme("old.png")
        with patch.object(_metadata, "MEMES_DIR", tmp_path):
            apply_migrations(conn)
        row = conn.execute("SELECT source_url, source_site FROM memes WHERE id = 'm1'").fetchone()
        assert row == (None, None)
