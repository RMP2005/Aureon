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
"""


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Get a synchronous SQLite connection.

    Uses a plain sqlite3 connection — no ORM overhead.
    WAL mode is enabled for better concurrent read performance.
    check_same_thread=False allows use from asyncio.to_thread.
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_default_connection() -> sqlite3.Connection:
    """Get the module-level default connection, creating one if needed."""
    global _default_conn
    if _default_conn is None:
        _default_conn = get_connection()
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
