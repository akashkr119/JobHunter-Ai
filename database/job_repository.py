"""Repository layer for persisting jobs."""

import sqlite3

from crawler.job_scraper import Job


class JobRepository:
    """Provides CRUD operations for scraped jobs."""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path

    def save_job(self, job: Job) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO jobs(title, company, location, apply_url)
            VALUES (?, ?, ?, ?)
            """,
            (job.title, job.company, job.location, job.apply_url),
        )
        conn.commit()
        conn.close()

    def get_all_jobs(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT title, company, location, apply_url FROM jobs")
        rows = cursor.fetchall()
        conn.close()
        return rows
