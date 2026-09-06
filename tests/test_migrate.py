import importlib
import sqlite3

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
