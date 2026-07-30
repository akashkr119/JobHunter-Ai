"""SQLite database utilities for JobHunter AI."""

import sqlite3
from pathlib import Path


class JobDatabase:
    """Manage job storage using SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    apply_url TEXT UNIQUE,
                    status TEXT DEFAULT 'new'
                )
                """
            )
            conn.commit()

    def insert_job(self, title: str, company: str, location: str, apply_url: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO jobs (title, company, location, apply_url) VALUES (?, ?, ?, ?)",
                (title, company, location, apply_url),
            )
            conn.commit()
