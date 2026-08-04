"""Command-line entry point for JobHunter AI."""

import argparse

from config.settings import Settings
from database.db import Database
from matcher.resume_parser import ResumeParser
from matcher.skill_matcher import SkillMatcher
from notifier.notifier import Notifier
from scheduler.scheduler import Scheduler


def build_scheduler(settings: Settings) -> Scheduler:
    """Build application services from centralized settings."""
    notifier = None
    if settings.notification_channel:
        notifier = Notifier(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_username=settings.smtp_username,
            smtp_password=settings.smtp_password,
            smtp_sender=settings.smtp_sender,
            telegram_bot_token=settings.telegram_bot_token,
        )

    return Scheduler(
        matcher=SkillMatcher(),
        database=Database(settings.database_path),
        notifier=notifier,
    )


def load_resume_skills(settings: Settings) -> list[str]:
    """Parse the configured resume and return detected skills."""
    parsed = ResumeParser().parse(settings.resume_path)
    return parsed["skills"]


def run_once(career_urls: list[str], settings: Settings) -> dict:
    """Execute one complete discovery run."""
    scheduler = build_scheduler(settings)
    try:
        return scheduler.run_pipeline(
            career_urls=career_urls,
            resume_skills=load_resume_skills(settings),
            min_score=settings.min_match_score,
            notification=settings.notification_config(),
        )
    finally:
        scheduler.database.close()


def run_scheduled(career_urls: list[str], settings: Settings) -> None:
    """Schedule the discovery pipeline and keep the process running."""
    scheduler = build_scheduler(settings)
    resume_skills = load_resume_skills(settings)
    scheduler.add_pipeline_job(
        career_urls=career_urls,
        resume_skills=resume_skills,
        hours=settings.scheduler_hours,
        min_score=settings.min_match_score,
        notification=settings.notification_config(),
    )
    try:
        scheduler.start()
    finally:
        scheduler.database.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JobHunter AI job discovery pipeline")
    parser.add_argument(
        "career_urls",
        nargs="+",
        help="Company career/ATS URLs to scan",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run continuously using JOBHUNTER_SCHEDULER_HOURS",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional path to a .env configuration file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env(args.env_file)

    if args.scheduled:
        run_scheduled(args.career_urls, settings)
        return 0

    summary = run_once(args.career_urls, settings)
    print(
        "JobHunter run complete: "
        f"found={summary['jobs_found']} "
        f"saved={summary['jobs_saved']} "
        f"skipped={summary['jobs_skipped']} "
        f"notifications={summary['notifications_sent']} "
        f"errors={len(summary['errors'])}"
    )
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
