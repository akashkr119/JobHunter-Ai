"""Repository for storing job match results."""

import sqlite3


class MatchRepository:
    """CRUD operations for job match records."""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path

    def save_match(self, job_id: int, resume_id: int, score: float, matched_skills: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO job_matches(job_id, resume_id, score, matched_skills) VALUES (?, ?, ?, ?)",
            (job_id, resume_id, score, matched_skills),
        )
        conn.commit()
        conn.close()

    def get_top_matches(self, limit: int = 10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT job_id, resume_id, score, matched_skills FROM job_matches ORDER BY score DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
