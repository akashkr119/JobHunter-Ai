"""Resume-first, multi-platform discovery orchestration for the dashboard.

Users upload a resume and choose locations; they never need to provide career
URLs for normal discovery. The discovery layer queries independent job-board
sources, isolates source failures, deduplicates listings, then hands the
normalized jobs to the existing matching/ranking pipeline.
"""
from __future__ import annotations

import os
from collections.abc import Iterable

from config.settings import Settings
from crawler.adzuna_source import AdzunaSource
from crawler.discovery import DiscoveryResult, JobDiscovery
from crawler.job_scraper import Job
from crawler.jobspy_source import JobSpySource
from crawler.source_manager import JobSourceManager
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from matcher.resume_parser import ResumeParser
from notifier.notifier import Notifier
from scheduler.scheduler import Scheduler

DEFAULT_JOBSPY_SOURCES = (
    "linkedin",
    "indeed",
    "naukri",
    "glassdoor",
    "google",
    "bayt",
    "bdjobs",
    "zip_recruiter",
)


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


def _source_names() -> tuple[str, ...]:
    """Return the platform set without requiring career URLs or credentials."""
    configured = tuple(
        name.strip().lower()
        for name in os.getenv("JOBHUNTER_SOURCES", "").split(",")
        if name.strip()
    )
    names = configured or DEFAULT_JOBSPY_SOURCES
    disabled = {
        name.strip().lower()
        for name in os.getenv("JOBHUNTER_DISABLED_SOURCES", "").split(",")
        if name.strip()
    }
    return tuple(name for name in names if name not in disabled)


def _build_source_manager() -> JobSourceManager:
    """Build all discovery sources used by the dashboard.

    Adzuna remains supported as an optional API source. It is only added when
    explicitly requested or when its credentials are present, so a missing
    Adzuna key can never prevent LinkedIn/Indeed/Naukri/etc. from running.
    """
    names = _source_names()
    sources = [JobSpySource(name) for name in names if name in DEFAULT_JOBSPY_SOURCES]
    if "adzuna" in names:
        sources.append(AdzunaSource())
    elif os.getenv("JOBHUNTER_ADZUNA_APP_ID") and os.getenv("JOBHUNTER_ADZUNA_APP_KEY"):
        sources.append(AdzunaSource())
    return JobSourceManager(sources)


def _discover(settings: Settings) -> DiscoveryResult:
    manager = _build_source_manager()
    discovery = JobDiscovery(manager)
    jobs: list[Job] = []
    runs = []
    provenance = []
    seen: set[str] = set()

    for role, location in _queries(settings):
        result = discovery.discover(
            role,
            sources=manager.names(),
            location=location,
            results_wanted=25,
            hours_old=72,
            country_indeed="India",
            is_remote=location.strip().lower() == "remote",
        )
        for job in result.jobs:
            key = str(job.apply_url).strip().rstrip("/").lower()
            if key and key not in seen:
                seen.add(key)
                jobs.append(job)
        runs.extend(result.runs)
        provenance.extend(result.provenance)

    return DiscoveryResult(tuple(jobs), tuple(runs), tuple(provenance))


def discover_jobs(settings: Settings) -> list[Job]:
    """Discover jobs across all enabled platforms without career URLs."""
    return list(_discover(settings).jobs)


def run_discovery(settings: Settings) -> dict:
    """Discover, match, rank and persist jobs for one configured user."""
    discovery = _discover(settings)
    jobs = list(discovery.jobs)
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
        summary = scheduler.run_discovered_jobs(
            jobs,
            resume_skills=resume_skills,
            min_score=settings.min_match_score,
            notification=settings.notification_config(),
            preferences=settings.job_preferences(),
        )
        source_summary: dict[str, dict[str, object]] = {}
        for run in discovery.runs:
            entry = source_summary.setdefault(run.source, {"jobs_found": 0, "errors": []})
            entry["jobs_found"] = int(entry["jobs_found"]) + len(run.jobs)
            if run.error:
                entry["errors"].append(run.error)
        summary["sources"] = source_summary
        summary["sources_attempted"] = len(source_summary)
        summary["sources_with_errors"] = [name for name, data in source_summary.items() if data["errors"]]
        return summary
    finally:
        scheduler.database.close()
