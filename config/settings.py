"""Centralized application settings for JobHunter AI."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "jobs.db"

USER_AGENT = "JobHunterAI/1.0"
REQUEST_TIMEOUT = 30
ALERT_PRIORITIES = {"apply_now", "high", "medium", "low"}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    database_path: str = str(DATABASE_PATH)
    resume_path: str = "resume.pdf"
    min_match_score: float = 60.0
    scheduler_hours: int = 6
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    email_recipient: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    notification_channel: str | None = None
    notification_min_priority: str = "apply_now"

    @classmethod
    def from_env(cls, env_file: str | None = None) -> "Settings":
        """Load configuration from an optional .env file and environment."""
        load_dotenv(dotenv_path=env_file, override=False)
        settings = cls(
            database_path=os.getenv("JOBHUNTER_DATABASE_PATH", str(DATABASE_PATH)),
            resume_path=os.getenv("JOBHUNTER_RESUME_PATH", "resume.pdf"),
            min_match_score=_float_env("JOBHUNTER_MIN_MATCH_SCORE", 60.0),
            scheduler_hours=_int_env("JOBHUNTER_SCHEDULER_HOURS", 6),
            smtp_host=_optional_env("JOBHUNTER_SMTP_HOST"),
            smtp_port=_int_env("JOBHUNTER_SMTP_PORT", 587),
            smtp_username=_optional_env("JOBHUNTER_SMTP_USERNAME"),
            smtp_password=_optional_env("JOBHUNTER_SMTP_PASSWORD"),
            smtp_sender=_optional_env("JOBHUNTER_SMTP_SENDER"),
            email_recipient=_optional_env("JOBHUNTER_EMAIL_RECIPIENT"),
            telegram_bot_token=_optional_env("JOBHUNTER_TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_optional_env("JOBHUNTER_TELEGRAM_CHAT_ID"),
            notification_channel=_optional_env("JOBHUNTER_NOTIFICATION_CHANNEL"),
            notification_min_priority=os.getenv("JOBHUNTER_NOTIFICATION_MIN_PRIORITY", "apply_now").strip().lower() or "apply_now",
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Validate ranges and supported configuration values."""
        if not 0 <= self.min_match_score <= 100:
            raise ValueError("JOBHUNTER_MIN_MATCH_SCORE must be between 0 and 100")
        if self.scheduler_hours <= 0:
            raise ValueError("JOBHUNTER_SCHEDULER_HOURS must be greater than zero")
        if not 1 <= self.smtp_port <= 65535:
            raise ValueError("JOBHUNTER_SMTP_PORT must be between 1 and 65535")
        channel = (self.notification_channel or "").strip().lower()
        if channel not in {"", "email", "telegram"}:
            raise ValueError("JOBHUNTER_NOTIFICATION_CHANNEL must be email or telegram")
        if self.notification_min_priority not in ALERT_PRIORITIES:
            raise ValueError("JOBHUNTER_NOTIFICATION_MIN_PRIORITY must be apply_now, high, medium or low")

    def notification_config(self) -> dict | None:
        """Return Scheduler-compatible smart notification configuration."""
        channel = (self.notification_channel or "").strip().lower()
        if not channel:
            return None
        config = {"minimum_priority": self.notification_min_priority}
        if channel == "telegram":
            if not self.telegram_bot_token or not self.telegram_chat_id:
                raise ValueError("Telegram notification requires bot token and chat id")
            return {"channel": "telegram", "chat_id": self.telegram_chat_id, **config}
        if not self.smtp_host or not self.smtp_sender or not self.email_recipient:
            raise ValueError("Email notification requires SMTP host, sender and recipient")
        return {"channel": "email", "recipient": self.email_recipient, **config}


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
