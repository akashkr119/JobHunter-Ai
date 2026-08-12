"""Command-line entry point for JobHunter AI."""

import argparse
from pathlib import Path
from urllib.parse import urlparse

from config.settings import Settings
from crawler.adzuna_source import AdzunaSource
from crawler.job_source import JobSearchRequest
from crawler.jooble_source import JoobleSource
from crawler.source_pipeline import process_source_jobs
from database.db import Database
from matcher.resume_parser import ResumeParser
from matcher.skill_matcher import SkillMatcher
from notifier.notifier import Notifier
from runner.production_runner import ProductionRunner
from scheduler.scheduler import Scheduler


def build_scheduler(settings: Settings) -> Scheduler:
    """Build the runtime with configured API-backed job sources."""
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

    sources = []
    if settings.adzuna_app_id and settings.adzuna_app_key:
        sources.append(
            AdzunaSource(
                app_id=settings.adzuna_app_id,
                app_key=settings.adzuna_app_key,
            )
        )
    if settings.jooble_api_key:
        sources.append(JoobleSource(api_key=settings.jooble_api_key))

    from crawler.job_source import JobSourceManager

    source_manager = JobSourceManager(sources=sources)
    return Scheduler(
        matcher=SkillMatcher(),
        database=Database(settings.database_path),
        notifier=notifier,
        source_manager=source_manager,
    )


def load_resume_skills(settings: Settings) -> list[str]:
    return ResumeParser().parse(settings.resume_path)["skills"]


def validate_startup(career_urls: list[str], settings: Settings) -> None:
    """Validate runtime inputs without requiring an Excel/company file."""
    resume = Path(settings.resume_path)
    if not resume.is_file():
        raise ValueError(f"Resume file not found: {resume}")

    has_source_credentials = bool(
        (settings.adzuna_app_id and settings.adzuna_app_key)
        or settings.jooble_api_key
    )
    if not career_urls and not has_source_credentials:
        raise ValueError(
            "No job sources configured. Provide career URLs or configure "
            "Adzuna/Jooble API credentials."
        )

    for url in career_urls:
        parsed = urlparse(str(url).strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid career URL: {url}")

    Path(settings.database_path).expanduser().resolve().parent.mkdir(
        parents=True, exist_ok=True
    )
    settings.notification_config()


def _empty_source_summary() -> dict:
    return {
        "sources": 0,
        "jobs_found": 0,
        "jobs_saved": 0,
        "jobs_skipped": 0,
        "jobs_preference_excluded": 0,
        "notifications_sent": 0,
        "notifications_suppressed": 0,
        "errors": [],
    }


def run_once(career_urls: list[str], settings: Settings) -> dict:
    """Run direct career URLs plus all configured API-backed job sources."""
    scheduler = build_scheduler(settings)
    try:
        resume_skills = load_resume_skills(settings)
        notification = settings.notification_config()
        preferences = settings.job_preferences()
        summary = _empty_source_summary()

        if career_urls:
            summary = scheduler.run_pipeline(
                career_urls=career_urls,
                resume_skills=resume_skills,
                min_score=settings.min_match_score,
                notification=notification,
                preferences=preferences,
            )

        request = JobSearchRequest(
            keywords=settings.target_titles or settings.desired_keywords,
            locations=settings.preferred_locations,
            remote="remote" in settings.work_modes,
            limit=settings.source_limit,
        )

        source_names = scheduler.source_manager.names()
        for source_name in source_names:
            source_summary = process_source_jobs(
                scheduler,
                request,
                resume_skills,
                sources=(source_name,),
                min_score=settings.min_match_score,
                notification=notification,
                preferences=preferences,
            )
            for key in (
                "jobs_found",
                "jobs_saved",
                "jobs_skipped",
                "jobs_preference_excluded",
                "notifications_sent",
                "notifications_suppressed",
            ):
                summary[key] = summary.get(key, 0) + source_summary.get(key, 0)
            summary["errors"].extend(source_summary.get("errors", []))

        summary["source_jobs_found"] = sum(
            process.get("jobs_found", 0) for process in []
        )
        summary["source_count"] = len(source_names)
        return summary
    finally:
        scheduler.database.close()


def run_scheduled(career_urls: list[str], settings: Settings) -> None:
    scheduler = build_scheduler(settings)
    ProductionRunner(
        scheduler,
        career_urls,
        load_resume_skills(settings),
        settings,
    ).start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="JobHunter AI multi-source job discovery pipeline"
    )
    parser.add_argument(
        "career_urls",
        nargs="*",
        help="Optional company career/ATS URLs to scan in addition to configured job sources",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env()
    try:
        career_urls = list(args.career_urls)
        validate_startup(career_urls, settings)
        summary = run_once(career_urls, settings)
        print(
            "JobHunter run complete: "
            f"found={summary['jobs_found']} "
            f"saved={summary['jobs_saved']} "
            f"sources={summary.get('source_count', 0)} "
            f"skipped={summary['jobs_skipped']} "
            f"notifications={summary.get('notifications_sent', 0)} "
            f"errors={len(summary['errors'])}"
        )
        return 0 if not summary["errors"] else 1
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
