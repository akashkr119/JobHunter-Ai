"""Command-line entry point for JobHunter AI."""

import argparse

from config.settings import Settings
from crawler.career_finder import CareerFinder
from crawler.company_loader import CompanyLoader
from crawler.website_finder import WebsiteFinder
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
    return ResumeParser().parse(settings.resume_path)["skills"]


def load_career_urls(excel_path: str, discover: bool = True) -> list[str]:
    """Resolve career URLs from structured company Excel input.

    Explicit career URLs are preferred. For rows containing only a company
    website, JobHunter can inspect the homepage for actual Careers/Jobs links
    and then append deterministic fallback candidates.
    """
    targets = CompanyLoader().load_targets(excel_path)
    career_finder = CareerFinder()
    website_finder = WebsiteFinder()
    urls: list[str] = []
    seen: set[str] = set()

    for target in targets:
        career_url = target.get("career_url")
        if career_url:
            candidates = [website_finder.normalize_url(career_url)]
        elif target.get("website"):
            website = website_finder.find(target["company"], target["website"])
            candidates = career_finder.find(website, discover=discover)
        else:
            continue

        for url in candidates:
            if url not in seen:
                seen.add(url)
                urls.append(url)

    return urls


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
    parser.add_argument("career_urls", nargs="*", help="Company career/ATS URLs to scan")
    parser.add_argument(
        "--companies",
        help="Excel file containing Company, Website and/or Career URL columns",
    )
    parser.add_argument(
        "--no-discovery",
        action="store_true",
        help="Do not fetch company homepages; use common career URL candidates only",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run continuously using JOBHUNTER_SCHEDULER_HOURS",
    )
    parser.add_argument(
        "--env-file", default=None, help="Optional path to a .env configuration file"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env(args.env_file)
    career_urls = list(args.career_urls)
    if args.companies:
        career_urls.extend(
            load_career_urls(args.companies, discover=not args.no_discovery)
        )
    career_urls = list(dict.fromkeys(career_urls))
    if not career_urls:
        raise SystemExit("Provide at least one career URL or --companies Excel file")

    if args.scheduled:
        run_scheduled(career_urls, settings)
        return 0

    summary = run_once(career_urls, settings)
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
