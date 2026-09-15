"""Resume-first discovery orchestration for the dashboard.

The dashboard does not require users to enter career URLs. A configured job
source is queried using the user's detected/approved roles and selected
locations, then the existing scheduler performs matching, ranking and alerts.
"""
from __future__ import annotations

from collections.abc import Iterable

from config.settings import Settings
from crawler.adzuna_source import AdzunaSource
from crawler.job_scraper import Job
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from matcher.resume_parser import ResumeParser
from matcher.job_preferences import JobPreferences
from notifier.notifier import Notifier
from scheduler.scheduler import Scheduler


def _queries(settings: Settings) -> Iterable[tuple[str, str]]:
    roles = tuple(settings.target_titles)
    locations = tuple(settings.preferred_locations)
    if not roles:
        raise ValueError("No target roles were detected. Upload a resume with job-title information or add a target role.")
    if not locations:
        raise ValueError("Select at least one preferred location before discovery.")
    for role in roles:
        for location in locations:
            yield role, location


def discover_jobs(settings: Settings) -> list[Job]:
    """Discover jobs without requiring a user-supplied career URL.

    Adzuna is the first source wired into the resume-first dashboard because it
    accepts free-form role/location queries and returns normalized job records.
    Additional authorized sources can be added behind the same function later.
    """
    source = AdzunaSource()
    jobs: list[Job] = []
    seen: set[str] = set()
    for role, location in _queries(settings):
        for job in source.search(role, location=location, results_per_page=50):
            key = str(job.apply_url).strip().rstrip("/").lower()
            if key and key not in seen:
                seen.add(key)
                jobs.append(job)
    return jobs


def run_discovery(settings: Settings) -> dict:
    """Discover, match, rank and persist jobs for one configured user."""
    jobs = discover_jobs(settings)
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
    scheduler = Scheduler(matcher=SkillMatcher(), database=Database(settings.database_path), notifier=notifier)
    try:
        resume_skills = ResumeParser().parse(settings.resume_path)["skills"]
        return scheduler.run_discovered_jobs(
            jobs,
            resume_skills=resume_skills,
            min_score=settings.min_match_score,
            notification=settings.notification_config(),
            preferences=settings.job_preferences(),
        )
    finally:
        scheduler.database.close()
