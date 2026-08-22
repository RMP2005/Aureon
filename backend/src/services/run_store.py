"""Persistent storage for simulation runs using SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from src.core.database import get_default_connection

logger = logging.getLogger("aureon.services.run_store")


class RunStore:
    """SQLite-backed persistence for simulation run results."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._db_path:
                from src.core.database import get_connection
                self._conn = get_connection(self._db_path)
            else:
                self._conn = get_default_connection()
        return self._conn

    def save_run(
        self,
        run_id: str,
        data: dict[str, Any] | None = None,
        *,
        run_type: str = "single_run",
        status: str = "completed",
        error_message: str | None = None,
    ) -> None:
        """Persist a simulation run result."""
        if data is None:
            data = {}
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO simulation_runs
               (run_id, run_type, strategy, parameters, status,
                result_summary, full_result, error_message,
                created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                run_type,
                data.get("strategy"),
                json.dumps(data.get("parameters", {})),
                status,
                json.dumps(self._extract_summary(data)),
                json.dumps(data),
                error_message,
                data.get("executed_at", ""),
                data.get("executed_at") if status == "completed" else None,
            ),
        )
        conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a single run by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT full_result FROM simulation_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["full_result"])

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        """List run summaries, most recent first."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT run_id, run_type, strategy, status, created_at
               FROM simulation_runs
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "type": row["run_type"],
                "strategy": row["strategy"],
                "status": row["status"],
                "executed_at": row["created_at"],
            }
            for row in rows
        ]

    def count_runs(self) -> int:
        """Return total number of stored runs."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM simulation_runs").fetchone()
        return row["cnt"]

    def delete_run(self, run_id: str) -> bool:
        """Delete a run. Returns True if a row was deleted."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM simulation_runs WHERE run_id = ?", (run_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _extract_summary(data: dict[str, Any]) -> dict[str, Any]:
        """Extract a lightweight summary from a full result dict."""
        metrics = data.get("metrics", {})
        if metrics:
            return {
                "total_incidents": metrics.get("total_incidents_reported", 0),
                "dispatched": metrics.get("total_incidents_dispatched", 0),
                "avg_response_time": metrics.get("average_response_time_minutes"),
            }
        # Comparison results
        if "improvements" in data:
            return {"improvements": data["improvements"]}
        return {}
