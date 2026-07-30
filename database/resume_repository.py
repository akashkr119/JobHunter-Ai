"""Repository layer for storing parsed resume data."""

import sqlite3


class ResumeRepository:
    """Provides CRUD operations for resume information."""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path

    def save_resume(self, name: str, email: str, skills: str, experience: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO resumes(name, email, skills, experience) VALUES (?, ?, ?, ?)",
            (name, email, skills, experience),
        )
        conn.commit()
        conn.close()

    def get_resume(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, skills, experience FROM resumes LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row
