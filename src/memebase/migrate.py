"""Lightweight SQLite migration runner using PRAGMA user_version."""

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
    log.info("schema now at version %d", get_version(conn))


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
