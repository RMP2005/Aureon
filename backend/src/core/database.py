"""SQLite database initialization for Aureon backend."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("aureon.database")

DEFAULT_DB_PATH = Path("aureon.db")

# Module-level default connection (set by init_db)
_default_conn: sqlite3.Connection | None = None

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id          TEXT PRIMARY KEY,
    run_type        TEXT NOT NULL DEFAULT 'single_run',
    strategy        TEXT,
    parameters      TEXT,
    status          TEXT NOT NULL DEFAULT 'completed',
    result_summary  TEXT,
    full_result     TEXT,
    error_message   TEXT,
    created_at      TEXT NOT NULL,
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS run_recordings (
    run_id             TEXT PRIMARY KEY,
    strategy           TEXT,
    duration_seconds   REAL,
    frame_count        INTEGER,
    frame_interval_sec REAL,
    event_count        INTEGER,
    payload            BLOB NOT NULL,
    created_at         TEXT NOT NULL
);
"""


def _prune_orphan_sidecars(path: Path) -> None:
    """Remove WAL sidecars that cannot belong to *path*'s database.

    SQLite in WAL mode fails with "disk I/O error" when the main database
    file is missing but a stale ``-wal``/``-shm`` pair from an earlier
    incarnation is present (e.g. a repo copied without the .db, or a
    backup restored without its sidecars). Sidecars are meaningless
    without their main file — deleting them lets SQLite start clean.
    """
    if path.exists():
        return
    for suffix in ("-wal", "-shm"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists():
            try:
                sidecar.unlink()
                logger.info("Removed orphaned WAL sidecar %s", sidecar)
            except OSError:
                logger.warning("Could not remove stale sidecar %s", sidecar)


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Get a synchronous SQLite connection.

    Uses a plain sqlite3 connection — no ORM overhead.
    WAL mode is enabled for better concurrent read performance.
    check_same_thread=False allows use from asyncio.to_thread.
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    _prune_orphan_sidecars(path)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_default_connection() -> sqlite3.Connection:
    """Get the module-level default connection, creating one if needed.

    The schema is applied idempotently (CREATE TABLE IF NOT EXISTS), so any
    consumer — API server, background worker thread, or library caller —
    gets a usable store even if init_db() never ran (Phase 10F-1 fix: a
    fresh or restored DB file previously crashed persistence with
    "no such table").
    """
    global _default_conn
    if _default_conn is None:
        _default_conn = get_connection()
        _default_conn.executescript(_SCHEMA_SQL)
        _default_conn.commit()
    return _default_conn


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Initialize the database schema and return a connection.

    Also sets the module-level default connection for RunStore to use.
    """
    global _default_conn
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    _default_conn = conn
    logger.info("Database initialized at %s", db_path or DEFAULT_DB_PATH)
    return conn
