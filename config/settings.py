"""Application settings for JobHunter AI."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "jobs.db"

USER_AGENT = "JobHunterAI/1.0"
REQUEST_TIMEOUT = 30
