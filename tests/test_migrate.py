import sqlite3

from memebase.migrate import apply_migrations, get_version, set_version


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
        assert get_version(conn) == 1
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
        assert get_version(conn) == 1
        # Running again should be a no-op
        apply_migrations(conn)
        assert get_version(conn) == 1
