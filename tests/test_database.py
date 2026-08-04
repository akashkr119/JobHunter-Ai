"""Unit tests for database layer."""

import pytest

from crawler.job_scraper import Job
from database.db import Database


def test_database_instance(tmp_path):
    db = Database(tmp_path / "jobs.db")
    assert db is not None
    db.close()


def test_has_connect_method(tmp_path):
    db = Database(tmp_path / "jobs.db")
    assert hasattr(db, "connect")
    assert db.connect() is not None
    db.close()


def test_has_save_job_method(tmp_path):
    db = Database(tmp_path / "jobs.db")
    assert hasattr(db, "save_job")
    assert callable(db.save_job)
    db.close()


def test_save_and_get_job(tmp_path):
    db = Database(tmp_path / "jobs.db")
    job = Job(
        title="QA Automation Engineer",
        company="Example",
        location="Bengaluru",
        apply_url="https://example.com/jobs/1",
        description="Python Selenium Pytest",
        platform="greenhouse",
    )

    job_id = db.save_job(
        job,
        match={
            "score": 75.0,
            "matched_skills": ["python", "selenium", "pytest"],
            "missing_skills": ["docker"],
        },
    )
    stored = db.get_job(job_id)

    assert stored is not None
    assert stored["title"] == "QA Automation Engineer"
    assert stored["company"] == "Example"
    assert stored["match_score"] == 75.0
    assert stored["matched_skills"] == ["python", "selenium", "pytest"]
    assert stored["missing_skills"] == ["docker"]
    db.close()


def test_duplicate_apply_url_updates_existing_job(tmp_path):
    db = Database(tmp_path / "jobs.db")
    url = "https://example.com/jobs/1"

    first_id = db.save_job(
        {
            "title": "QA Engineer",
            "company": "Example",
            "location": "Pune",
            "apply_url": url,
            "description": "Python",
            "platform": "greenhouse",
        },
        match={"score": 50.0},
    )
    second_id = db.save_job(
        {
            "title": "Senior QA Engineer",
            "company": "Example",
            "location": "Bengaluru",
            "apply_url": url,
            "description": "Python Selenium",
            "platform": "greenhouse",
        },
        match={"score": 90.0},
    )

    jobs = db.list_jobs()
    assert len(jobs) == 1
    assert first_id == second_id
    assert jobs[0]["title"] == "Senior QA Engineer"
    assert jobs[0]["location"] == "Bengaluru"
    assert jobs[0]["match_score"] == 90.0
    db.close()


def test_list_jobs_orders_by_match_score(tmp_path):
    db = Database(tmp_path / "jobs.db")
    db.save_job(
        {
            "title": "Job A",
            "company": "A",
            "apply_url": "https://example.com/a",
        },
        match={"score": 40.0},
    )
    db.save_job(
        {
            "title": "Job B",
            "company": "B",
            "apply_url": "https://example.com/b",
        },
        match={"score": 85.0},
    )

    jobs = db.list_jobs()
    assert [job["title"] for job in jobs] == ["Job B", "Job A"]
    db.close()


def test_list_jobs_filters_minimum_score(tmp_path):
    db = Database(tmp_path / "jobs.db")
    db.save_job(
        {"title": "Low", "company": "A", "apply_url": "https://example.com/low"},
        match={"score": 30.0},
    )
    db.save_job(
        {"title": "High", "company": "B", "apply_url": "https://example.com/high"},
        match={"score": 80.0},
    )

    jobs = db.list_jobs(min_score=60)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "High"
    db.close()


def test_save_job_requires_apply_url(tmp_path):
    db = Database(tmp_path / "jobs.db")
    with pytest.raises(ValueError, match="apply_url"):
        db.save_job({"title": "QA", "company": "Example"})
    db.close()


def test_database_persists_after_reopen(tmp_path):
    path = tmp_path / "jobs.db"
    db = Database(path)
    job_id = db.save_job(
        {
            "title": "Persistent Job",
            "company": "Example",
            "apply_url": "https://example.com/persistent",
        }
    )
    db.close()

    reopened = Database(path)
    stored = reopened.get_job(job_id)
    assert stored is not None
    assert stored["title"] == "Persistent Job"
    reopened.close()
