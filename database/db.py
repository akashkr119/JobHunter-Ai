"""SQLite persistence for discovered and matched jobs."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path


class Database:
    """Store normalized jobs and resume-match results in SQLite."""

    def __init__(self, db_path: str | Path = "jobs.db") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def connect(self) -> sqlite3.Connection:
        """Return the active SQLite connection."""
        return self.conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a write/query statement and commit it."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def fetchall(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute a query and return all rows."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_job(self, job, match: dict | None = None) -> int:
        """Insert or update a job, deduplicating by its apply URL."""
        data = self._job_dict(job)
        apply_url = str(data.get("apply_url") or "").strip()
        title = str(data.get("title") or "").strip()
        company = str(data.get("company") or "").strip()

        if not apply_url:
            raise ValueError("Job apply_url is required")
        if not title:
            raise ValueError("Job title is required")
        if not company:
            raise ValueError("Job company is required")

        match = match or {}
        matched_skills = match.get("matched_skills") or []
        missing_skills = match.get("missing_skills") or []
        score = float(match.get("score", 0.0))

        cursor = self.execute(
            """
            INSERT INTO jobs (
                title, company, location, apply_url, description, platform,
                match_score, matched_skills, missing_skills
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(apply_url) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                location = excluded.location,
                description = excluded.description,
                platform = excluded.platform,
                match_score = excluded.match_score,
                matched_skills = excluded.matched_skills,
                missing_skills = excluded.missing_skills,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                title,
                company,
                str(data.get("location") or "").strip(),
                apply_url,
                str(data.get("description") or "").strip(),
                str(data.get("platform") or "unknown").strip().lower(),
                score,
                json.dumps(list(matched_skills)),
                json.dumps(list(missing_skills)),
            ),
        )

        if cursor.lastrowid:
            return int(cursor.lastrowid)

        row = self.conn.execute(
            "SELECT id FROM jobs WHERE apply_url = ?", (apply_url,)
        ).fetchone()
        return int(row["id"])

    def save_jobs(self, jobs: Iterable, matches: dict[str, dict] | None = None) -> list[int]:
        """Persist multiple jobs and return their database IDs."""
        matches = matches or {}
        ids: list[int] = []
        for job in jobs:
            data = self._job_dict(job)
            match = matches.get(str(data.get("apply_url") or ""))
            ids.append(self.save_job(job, match=match))
        return ids

    def list_jobs(self, min_score: float = 0.0, limit: int = 100) -> list[dict]:
        """Return jobs ordered by match score and newest discovery time."""
        rows = self.fetchall(
            """
            SELECT * FROM jobs
            WHERE match_score >= ?
            ORDER BY match_score DESC, discovered_at DESC
            LIMIT ?
            """,
            (float(min_score), int(limit)),
        )
        return [self._row_to_dict(row) for row in rows]

    def get_job(self, job_id: int) -> dict | None:
        """Return one job by database ID."""
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def close(self) -> None:
        """Close the SQLite connection."""
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                apply_url TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT 'unknown',
                match_score REAL NOT NULL DEFAULT 0,
                matched_skills TEXT NOT NULL DEFAULT '[]',
                missing_skills TEXT NOT NULL DEFAULT '[]',
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)"
        )
        self.conn.commit()

    @staticmethod
    def _job_dict(job) -> dict:
        if isinstance(job, dict):
            return job
        if hasattr(job, "to_dict"):
            return job.to_dict()
        return {
            "title": getattr(job, "title", ""),
            "company": getattr(job, "company", ""),
            "location": getattr(job, "location", ""),
            "apply_url": getattr(job, "apply_url", ""),
            "description": getattr(job, "description", ""),
            "platform": getattr(job, "platform", "unknown"),
        }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["matched_skills"] = json.loads(result.get("matched_skills") or "[]")
        result["missing_skills"] = json.loads(result.get("missing_skills") or "[]")
        return result
