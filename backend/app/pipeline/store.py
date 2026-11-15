"""SQLite-backed job table for pipeline stages.

One row per (department, professor, stage). Status is one of pending,
running, done, failed. A row's `result` holds the JSON-serialized output of
that stage, so a resumed run can skip finished stages while still feeding
their output forward to later stages.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PENDING = "pending"
RUNNING = "running"
DONE = "done"
FAILED = "failed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_jobs (
    department TEXT NOT NULL,
    professor TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    error TEXT,
    result TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (department, professor, stage)
)
"""


@dataclass
class JobRecord:
    department: str
    professor: str
    stage: str
    status: str
    attempts: int
    max_attempts: int
    error: str | None
    result: object | None
    updated_at: str

    @property
    def exhausted(self) -> bool:
        return self.status == FAILED and self.attempts >= self.max_attempts


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_record(row: sqlite3.Row) -> JobRecord:
    result = json.loads(row["result"]) if row["result"] is not None else None
    return JobRecord(
        department=row["department"],
        professor=row["professor"],
        stage=row["stage"],
        status=row["status"],
        attempts=row["attempts"],
        max_attempts=row["max_attempts"],
        error=row["error"],
        result=result,
        updated_at=row["updated_at"],
    )


class JobStore:
    """Tracks pipeline job state for every (department, professor, stage)."""

    def __init__(self, db_path: str | Path = "pipeline_state.db") -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> JobStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def get(self, department: str, professor: str, stage: str) -> JobRecord | None:
        row = self._conn.execute(
            "SELECT * FROM pipeline_jobs WHERE department = ? AND professor = ? "
            "AND stage = ?",
            (department, professor, stage),
        ).fetchone()
        return _row_to_record(row) if row else None

    def list_jobs(self, department: str | None = None) -> list[JobRecord]:
        if department is None:
            rows = self._conn.execute(
                "SELECT * FROM pipeline_jobs ORDER BY professor, stage"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM pipeline_jobs WHERE department = ? "
                "ORDER BY professor, stage",
                (department,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def seed_pending(
        self, department: str, professor: str, stage: str, max_attempts: int
    ) -> None:
        """Ensure a row exists for this stage so it's visible before it runs.

        No-op if a row already exists (at any status) - this must never
        clobber progress made by a previous run.
        """
        self._conn.execute(
            """
            INSERT OR IGNORE INTO pipeline_jobs
                (department, professor, stage, status, attempts, max_attempts,
                 error, result, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, NULL, NULL, ?)
            """,
            (department, professor, stage, PENDING, max_attempts, _now()),
        )
        self._conn.commit()

    def mark_running(
        self, department: str, professor: str, stage: str, max_attempts: int
    ) -> int:
        """Record a new attempt starting. Returns the attempt number."""
        existing = self.get(department, professor, stage)
        attempts = (existing.attempts if existing else 0) + 1
        self._conn.execute(
            """
            INSERT INTO pipeline_jobs
                (department, professor, stage, status, attempts, max_attempts,
                 error, result, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
            ON CONFLICT(department, professor, stage) DO UPDATE SET
                status = excluded.status,
                attempts = excluded.attempts,
                max_attempts = excluded.max_attempts,
                error = NULL,
                updated_at = excluded.updated_at
            """,
            (department, professor, stage, RUNNING, attempts, max_attempts, _now()),
        )
        self._conn.commit()
        return attempts

    def mark_done(
        self, department: str, professor: str, stage: str, result: object
    ) -> None:
        self._conn.execute(
            """
            UPDATE pipeline_jobs
            SET status = ?, error = NULL, result = ?, updated_at = ?
            WHERE department = ? AND professor = ? AND stage = ?
            """,
            (DONE, json.dumps(result), _now(), department, professor, stage),
        )
        self._conn.commit()

    def mark_failed(
        self, department: str, professor: str, stage: str, error: str
    ) -> None:
        self._conn.execute(
            """
            UPDATE pipeline_jobs
            SET status = ?, error = ?, updated_at = ?
            WHERE department = ? AND professor = ? AND stage = ?
            """,
            (FAILED, error, _now(), department, professor, stage),
        )
        self._conn.commit()
