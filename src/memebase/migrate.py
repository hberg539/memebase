"""Lightweight SQLite migration runner using PRAGMA user_version.

Each migration module provides ``migrate(conn)`` for schema changes and may
also provide ``post_migrate(conn)`` for one-time data work such as backfills.
"""

import importlib
import logging
import pkgutil
import sqlite3
from types import ModuleType

import memebase.migrations as migrations_pkg

log = logging.getLogger(__name__)


def get_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version from the database."""
    return conn.execute("PRAGMA user_version").fetchone()[0]


def set_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the schema version in the database."""
    conn.execute(f"PRAGMA user_version = {int(version)}")


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations to the database."""
    current = get_version(conn)
    pending = _discover_migrations(after=current)
    if not pending:
        log.debug("schema up to date at version %d", current)
        return
    log.info("schema at version %d, %d migration(s) pending", current, len(pending))
    for version, module in pending:
        log.info("applying migration %04d (%s)", version, module.__name__)
        module.migrate(conn)
        conn.commit()
        set_version(conn, version)
        _run_post_migrate(conn, version, module)
    log.info("schema now at version %d", get_version(conn))


def _run_post_migrate(conn: sqlite3.Connection, version: int, module: ModuleType) -> None:
    """Run a migration's optional post_migrate(conn) data hook.

    Hooks run once, right after their schema migration is applied and the
    version is bumped. They are for data work (backfills, cleanups) that
    must not block startup: failures are logged, not raised, so hooks
    should be idempotent and skip rows they already handled.
    """
    hook = getattr(module, "post_migrate", None)
    if hook is None:
        return
    log.info("running post-migrate hook for %04d", version)
    try:
        hook(conn)
        conn.commit()
    except Exception:
        log.exception("post-migrate hook for %04d failed", version)
        conn.rollback()


def _discover_migrations(after: int) -> list[tuple[int, ModuleType]]:
    """Find migration modules with version number > after, sorted ascending."""
    results: list[tuple[int, ModuleType]] = []
    for _importer, name, _ispkg in pkgutil.iter_modules(migrations_pkg.__path__):
        parts = name.split("_", 1)
        if not parts[0].isdigit():
            continue
        version = int(parts[0])
        if version <= after:
            continue
        module = importlib.import_module(f"memebase.migrations.{name}")
        results.append((version, module))
    results.sort(key=lambda x: x[0])
    return results
