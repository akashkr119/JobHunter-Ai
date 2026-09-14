"""Durable submission state used to prevent duplicate external actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class SubmissionState(str):
    """Persisted lifecycle states for one exact application package."""

    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"


@dataclass(frozen=True)
class PersistedSubmission:
    package_fingerprint: str
    approval_id: str
    state: str
    message: str
    failure_category: str | None
    updated_at: str


class SubmissionStateStore:
    """SQLite-backed idempotency store for application submission attempts.

    An in-progress record is deliberately treated as an unknown external outcome.
    It blocks a second attempt after a process crash rather than risking a duplicate
    submission. Failed attempts are explicitly retryable only when recorded as such.
    """

    def __init__(self, db_path: str | Path = "jobs.db") -> None:
        self.db_path = str(db_path)
        Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS submission_state(
                package_fingerprint TEXT PRIMARY KEY,
                approval_id TEXT NOT NULL,
                state TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                failure_category TEXT,
                updated_at TEXT NOT NULL
            )"""
        )
        columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(submission_state)")
        }
        if "failure_category" not in columns:
            self.conn.execute("ALTER TABLE submission_state ADD COLUMN failure_category TEXT")
        self.conn.commit()

    def get(self, package_fingerprint: str) -> PersistedSubmission | None:
        row = self.conn.execute(
            "SELECT package_fingerprint, approval_id, state, message, failure_category, updated_at "
            "FROM submission_state WHERE package_fingerprint=?",
            (package_fingerprint,),
        ).fetchone()
        if row is None:
            return None
        return PersistedSubmission(**dict(row))

    def claim(self, package_fingerprint: str, approval_id: str) -> PersistedSubmission:
        """Atomically reserve a package before any external submission call."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            row = cursor.execute(
                "SELECT package_fingerprint, approval_id, state, message, failure_category, updated_at "
                "FROM submission_state WHERE package_fingerprint=?",
                (package_fingerprint,),
            ).fetchone()
            if row is None:
                cursor.execute(
                    "INSERT INTO submission_state(package_fingerprint, approval_id, state, message, failure_category, updated_at) "
                    "VALUES(?, ?, ?, '', NULL, ?)",
                    (package_fingerprint, approval_id, SubmissionState.IN_PROGRESS, now),
                )
                result = self.get(package_fingerprint)
                self.conn.commit()
                assert result is not None
                return result
            state = str(row["state"])
            if state == SubmissionState.SUBMITTED:
                self.conn.rollback()
                raise RuntimeError("Application package has already been submitted")
            if state == SubmissionState.IN_PROGRESS:
                self.conn.rollback()
                raise RuntimeError(
                    "Application package has an unresolved submission attempt; "
                    "reconcile the external outcome before retrying"
                )
            cursor.execute(
                "UPDATE submission_state SET approval_id=?, state=?, message='', failure_category=NULL, updated_at=? "
                "WHERE package_fingerprint=?",
                (approval_id, SubmissionState.IN_PROGRESS, now, package_fingerprint),
            )
            result = self.get(package_fingerprint)
            self.conn.commit()
            assert result is not None
            return result
        except Exception:
            if self.conn.in_transaction:
                self.conn.rollback()
            raise

    def mark_submitted(self, package_fingerprint: str, message: str = "") -> PersistedSubmission:
        self._set(package_fingerprint, SubmissionState.SUBMITTED, message, None)
        result = self.get(package_fingerprint)
        assert result is not None
        return result

    def mark_failed(
        self,
        package_fingerprint: str,
        message: str,
        failure_category: str,
    ) -> PersistedSubmission:
        self._set(package_fingerprint, SubmissionState.FAILED, message, failure_category)
        result = self.get(package_fingerprint)
        assert result is not None
        return result

    def _set(
        self,
        package_fingerprint: str,
        state: str,
        message: str,
        failure_category: str | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            "UPDATE submission_state SET state=?, message=?, failure_category=?, updated_at=? WHERE package_fingerprint=?",
            (state, str(message), failure_category, now, package_fingerprint),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"Unknown submission package: {package_fingerprint}")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
