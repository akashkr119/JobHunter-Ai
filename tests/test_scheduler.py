"""Unit tests for scheduler and pipeline orchestration."""

import pytest

from crawler.job_scraper import Job
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from scheduler.scheduler import Scheduler


class FakeScraperFactory:
    """Deterministic scraper factory used to avoid network calls in tests."""

    def __init__(self, jobs_by_url=None, failing_urls=None):
        self.jobs_by_url = jobs_by_url or {}
        self.failing_urls = set(failing_urls or [])

    def scrape(self, career_url, company=""):
        if career_url in self.failing_urls:
            raise RuntimeError("scraper failed")
        return list(self.jobs_by_url.get(career_url, []))


class FakeNotifier:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    @staticmethod
    def format_job_alert(job, match):
        return f"{job.title}: {match['score']}%"

    def send(self, channel, **kwargs):
        if self.fail:
            raise RuntimeError("notification failed")
        self.sent.append((channel, kwargs))
        return {"success": True, "channel": channel}


def build_scheduler(tmp_path, factory=None, notifier=None):
    return Scheduler(
        scraper_factory=factory or FakeScraperFactory(),
        matcher=SkillMatcher(),
        database=Database(tmp_path / "jobs.db"),
        notifier=notifier,
    )


def sample_job(url="https://example.com/jobs/1", description="Python Selenium Pytest Docker"):
    return Job(
        title="QA Automation Engineer",
        company="Example",
        location="Bengaluru",
        apply_url=url,
        description=description,
        platform="greenhouse",
    )


def test_scheduler_instance(tmp_path):
    scheduler = build_scheduler(tmp_path)
    assert scheduler is not None
    scheduler.database.close()


def test_has_start_method(tmp_path):
    scheduler = build_scheduler(tmp_path)
    assert hasattr(scheduler, "start")
    scheduler.database.close()


def test_start_method_is_callable(tmp_path):
    scheduler = build_scheduler(tmp_path)
    assert callable(scheduler.start)
    scheduler.database.close()


def test_run_pipeline_scrapes_matches_and_saves_jobs(tmp_path):
    url = "https://boards.greenhouse.io/example"
    scheduler = build_scheduler(tmp_path, FakeScraperFactory({url: [sample_job()]}))

    summary = scheduler.run_pipeline(
        [url], ["python", "selenium", "pytest"], min_score=50
    )

    assert summary["sources"] == 1
    assert summary["jobs_found"] == 1
    assert summary["jobs_saved"] == 1
    assert summary["jobs_skipped"] == 0
    assert summary["notifications_sent"] == 0
    assert summary["errors"] == []

    jobs = scheduler.database.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["match_score"] == 75.0
    assert jobs[0]["missing_skills"] == ["docker"]
    scheduler.database.close()


def test_run_pipeline_filters_jobs_below_minimum_score(tmp_path):
    url = "https://jobs.lever.co/example"
    job = sample_job(
        url="https://example.com/jobs/2",
        description="Python Docker Kubernetes AWS",
    )
    scheduler = build_scheduler(tmp_path, FakeScraperFactory({url: [job]}))

    summary = scheduler.run_pipeline([url], ["python"], min_score=50)

    assert summary["jobs_found"] == 1
    assert summary["jobs_saved"] == 0
    assert summary["jobs_skipped"] == 1
    assert scheduler.database.list_jobs() == []
    scheduler.database.close()


def test_matching_job_sends_notification(tmp_path):
    url = "https://boards.greenhouse.io/example"
    notifier = FakeNotifier()
    scheduler = build_scheduler(
        tmp_path,
        FakeScraperFactory({url: [sample_job()]}),
        notifier=notifier,
    )

    summary = scheduler.run_pipeline(
        [url],
        ["python", "selenium", "pytest"],
        min_score=50,
        notification={"channel": "telegram", "chat_id": "12345"},
    )

    assert summary["jobs_saved"] == 1
    assert summary["notifications_sent"] == 1
    assert len(notifier.sent) == 1
    channel, kwargs = notifier.sent[0]
    assert channel == "telegram"
    assert kwargs["chat_id"] == "12345"
    assert "75.0%" in kwargs["message"]
    scheduler.database.close()


def test_below_threshold_job_does_not_send_notification(tmp_path):
    url = "https://jobs.lever.co/example"
    notifier = FakeNotifier()
    job = sample_job(description="Python Docker Kubernetes AWS")
    scheduler = build_scheduler(
        tmp_path, FakeScraperFactory({url: [job]}), notifier=notifier
    )

    summary = scheduler.run_pipeline(
        [url],
        ["python"],
        min_score=50,
        notification={"channel": "telegram", "chat_id": "123"},
    )

    assert summary["jobs_skipped"] == 1
    assert summary["notifications_sent"] == 0
    assert notifier.sent == []
    scheduler.database.close()


def test_notification_failure_does_not_lose_saved_job(tmp_path):
    url = "https://boards.greenhouse.io/example"
    notifier = FakeNotifier(fail=True)
    scheduler = build_scheduler(
        tmp_path,
        FakeScraperFactory({url: [sample_job()]}),
        notifier=notifier,
    )

    summary = scheduler.run_pipeline(
        [url],
        ["python", "selenium", "pytest"],
        min_score=50,
        notification={"channel": "telegram", "chat_id": "123"},
    )

    assert summary["jobs_saved"] == 1
    assert summary["notifications_sent"] == 0
    assert len(scheduler.database.list_jobs()) == 1
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["stage"] == "notify"
    scheduler.database.close()


def test_one_failed_source_does_not_stop_other_sources(tmp_path):
    bad_url = "https://example.com/bad"
    good_url = "https://boards.greenhouse.io/good"
    factory = FakeScraperFactory(
        {good_url: [sample_job(url="https://example.com/jobs/good", description="Python")]},
        failing_urls={bad_url},
    )
    scheduler = build_scheduler(tmp_path, factory)

    summary = scheduler.run_pipeline([bad_url, good_url], ["python"], min_score=50)

    assert summary["sources"] == 2
    assert summary["jobs_found"] == 1
    assert summary["jobs_saved"] == 1
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["career_url"] == bad_url
    assert summary["errors"][0]["stage"] == "scrape"
    scheduler.database.close()


def test_invalid_minimum_score_rejected(tmp_path):
    scheduler = build_scheduler(tmp_path)
    with pytest.raises(ValueError, match="min_score"):
        scheduler.run_pipeline([], ["python"], min_score=101)
    scheduler.database.close()


def test_add_job_rejects_non_positive_interval(tmp_path):
    scheduler = build_scheduler(tmp_path)
    with pytest.raises(ValueError, match="hours"):
        scheduler.add_job(lambda: None, hours=0)
    scheduler.database.close()


def test_add_pipeline_job_registers_interval_job(tmp_path):
    scheduler = build_scheduler(tmp_path)
    job = scheduler.add_pipeline_job(
        ["https://boards.greenhouse.io/example"],
        ["python", "selenium"],
        hours=2,
        min_score=60,
        notification={"channel": "telegram", "chat_id": "123"},
    )

    assert job is not None
    assert job.func == scheduler.run_pipeline
    scheduler.database.close()
