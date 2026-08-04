"""SQLite persistence for discovered, matched and tracked jobs."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path


class Database:
    """Store normalized jobs, match results and application progress."""

    MATCH_LIST_COLUMNS = (
        "matched_skills", "missing_skills", "required_skills", "preferred_skills",
        "general_skills", "matched_required_skills", "missing_required_skills",
    )
    APPLICATION_STATUSES = ("new", "viewed", "applied", "interview", "rejected", "offer")

    def __init__(self, db_path: str | Path = "jobs.db") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def connect(self) -> sqlite3.Connection:
        return self.conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        cursor = self.conn.cursor(); cursor.execute(query, params); self.conn.commit(); return cursor

    def fetchall(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        cursor = self.conn.cursor(); cursor.execute(query, params); return cursor.fetchall()

    def save_job(self, job, match: dict | None = None) -> int:
        """Insert/update a job while preserving its application status."""
        data = self._job_dict(job)
        apply_url = str(data.get("apply_url") or "").strip(); title = str(data.get("title") or "").strip(); company = str(data.get("company") or "").strip()
        if not apply_url: raise ValueError("Job apply_url is required")
        if not title: raise ValueError("Job title is required")
        if not company: raise ValueError("Job company is required")
        match = match or {}; score = float(match.get("score", 0.0)); lists = {name: list(match.get(name) or []) for name in self.MATCH_LIST_COLUMNS}
        cursor = self.execute("""
            INSERT INTO jobs (title, company, location, apply_url, description, platform, match_score, matched_skills, missing_skills, required_skills, preferred_skills, general_skills, matched_required_skills, missing_required_skills)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(apply_url) DO UPDATE SET title=excluded.title, company=excluded.company, location=excluded.location, description=excluded.description, platform=excluded.platform, match_score=excluded.match_score, matched_skills=excluded.matched_skills, missing_skills=excluded.missing_skills, required_skills=excluded.required_skills, preferred_skills=excluded.preferred_skills, general_skills=excluded.general_skills, matched_required_skills=excluded.matched_required_skills, missing_required_skills=excluded.missing_required_skills, updated_at=CURRENT_TIMESTAMP
        """, (title, company, str(data.get("location") or "").strip(), apply_url, str(data.get("description") or "").strip(), str(data.get("platform") or "unknown").strip().lower(), score, *(json.dumps(lists[name]) for name in self.MATCH_LIST_COLUMNS)))
        if cursor.lastrowid: return int(cursor.lastrowid)
        row = self.conn.execute("SELECT id FROM jobs WHERE apply_url = ?", (apply_url,)).fetchone(); return int(row["id"])

    def save_jobs(self, jobs: Iterable, matches: dict[str, dict] | None = None) -> list[int]:
        matches = matches or {}; ids = []
        for job in jobs:
            data = self._job_dict(job); ids.append(self.save_job(job, matches.get(str(data.get("apply_url") or ""))))
        return ids

    def update_application_status(self, job_id: int, status: str) -> dict:
        """Move a job through the application workflow."""
        normalized = str(status or "").strip().lower()
        if normalized not in self.APPLICATION_STATUSES:
            raise ValueError(f"Invalid application status: {status}")
        if self.get_job(job_id) is None:
            raise KeyError(f"Job not found: {job_id}")
        self.execute("UPDATE jobs SET application_status = ?, status_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (normalized, int(job_id)))
        return self.get_job(job_id)

    def list_jobs(self, min_score: float = 0.0, limit: int = 100, status: str | None = None) -> list[dict]:
        params: list = [float(min_score)]; where = "match_score >= ?"
        if status is not None:
            normalized = str(status).strip().lower()
            if normalized not in self.APPLICATION_STATUSES: raise ValueError(f"Invalid application status: {status}")
            where += " AND application_status = ?"; params.append(normalized)
        params.append(int(limit))
        rows = self.fetchall(f"SELECT * FROM jobs WHERE {where} ORDER BY match_score DESC, discovered_at DESC LIMIT ?", tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_job(self, job_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone(); return self._row_to_dict(row) if row else None

    def close(self) -> None: self.conn.close()

    def _create_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '', apply_url TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '', platform TEXT NOT NULL DEFAULT 'unknown',
                match_score REAL NOT NULL DEFAULT 0, matched_skills TEXT NOT NULL DEFAULT '[]', missing_skills TEXT NOT NULL DEFAULT '[]', required_skills TEXT NOT NULL DEFAULT '[]', preferred_skills TEXT NOT NULL DEFAULT '[]', general_skills TEXT NOT NULL DEFAULT '[]', matched_required_skills TEXT NOT NULL DEFAULT '[]', missing_required_skills TEXT NOT NULL DEFAULT '[]',
                application_status TEXT NOT NULL DEFAULT 'new', status_updated_at TEXT,
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._migrate_schema()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs(application_status)"); self.conn.commit()

    def _migrate_schema(self) -> None:
        existing = {row["name"] for row in self.conn.execute("PRAGMA table_info(jobs)").fetchall()}
        migrations = {
            "required_skills": "TEXT NOT NULL DEFAULT '[]'", "preferred_skills": "TEXT NOT NULL DEFAULT '[]'", "general_skills": "TEXT NOT NULL DEFAULT '[]'", "matched_required_skills": "TEXT NOT NULL DEFAULT '[]'", "missing_required_skills": "TEXT NOT NULL DEFAULT '[]'",
            "application_status": "TEXT NOT NULL DEFAULT 'new'", "status_updated_at": "TEXT",
        }
        for column, definition in migrations.items():
            if column not in existing: self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")

    @staticmethod
    def _job_dict(job) -> dict:
        if isinstance(job, dict): return job
        if hasattr(job, "to_dict"): return job.to_dict()
        return {"title": getattr(job, "title", ""), "company": getattr(job, "company", ""), "location": getattr(job, "location", ""), "apply_url": getattr(job, "apply_url", ""), "description": getattr(job, "description", ""), "platform": getattr(job, "platform", "unknown")}

    @classmethod
    def _row_to_dict(cls, row: sqlite3.Row) -> dict:
        result = dict(row)
        for column in cls.MATCH_LIST_COLUMNS: result[column] = json.loads(result.get(column) or "[]")
        return result
