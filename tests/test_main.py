"""Tests for the JobHunter application entry point."""

from unittest.mock import MagicMock, patch

import pandas as pd

from config.settings import Settings
from main import (
    build_scheduler,
    load_career_urls,
    load_resume_skills,
    run_once,
    run_scheduled,
)


def make_settings(tmp_path, **overrides):
    values = {
        "database_path": str(tmp_path / "jobs.db"),
        "resume_path": str(tmp_path / "resume.txt"),
        "min_match_score": 60.0,
        "scheduler_hours": 6,
    }
    values.update(overrides)
    return Settings(**values)


def test_build_scheduler_uses_configured_database(tmp_path):
    settings = make_settings(tmp_path)
    scheduler = build_scheduler(settings)
    try:
        assert scheduler.database.db_path == settings.database_path
        assert scheduler.notifier is None
    finally:
        scheduler.database.close()


def test_build_scheduler_creates_notifier_when_enabled(tmp_path):
    settings = make_settings(
        tmp_path,
        notification_channel="telegram",
        telegram_bot_token="token",
        telegram_chat_id="123",
    )
    scheduler = build_scheduler(settings)
    try:
        assert scheduler.notifier is not None
        assert scheduler.notifier.telegram_bot_token == "token"
    finally:
        scheduler.database.close()


def test_load_resume_skills(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python Selenium Pytest Docker", encoding="utf-8")
    settings = make_settings(tmp_path)
    skills = load_resume_skills(settings)
    assert {"python", "selenium", "pytest", "docker"}.issubset(skills)


def test_load_career_urls_prefers_explicit_career_url(tmp_path):
    workbook = tmp_path / "companies.xlsx"
    pd.DataFrame([{
        "Company": "Example",
        "Website": "https://example.com",
        "Career URL": "https://jobs.lever.co/example",
    }]).to_excel(workbook, index=False)

    urls = load_career_urls(str(workbook))

    assert urls == ["https://jobs.lever.co/example"]


def test_load_career_urls_offline_mode_generates_candidates(tmp_path):
    workbook = tmp_path / "companies.xlsx"
    pd.DataFrame([{"Company": "Example", "Website": "example.com"}]).to_excel(
        workbook, index=False
    )

    with patch("main.CareerFinder") as finder_class:
        finder = finder_class.return_value
        finder.find.return_value = [
            "https://example.com/careers",
            "https://example.com/jobs",
        ]
        urls = load_career_urls(str(workbook), discover=False)

    finder.find.assert_called_once_with("https://example.com", discover=False)
    assert urls == ["https://example.com/careers", "https://example.com/jobs"]


def test_load_career_urls_uses_discovered_ats_link(tmp_path):
    workbook = tmp_path / "companies.xlsx"
    pd.DataFrame([{"Company": "Example", "Website": "example.com"}]).to_excel(
        workbook, index=False
    )

    with patch("main.CareerFinder") as finder_class:
        finder = finder_class.return_value
        finder.find.return_value = [
            "https://boards.greenhouse.io/example",
            "https://example.com/careers",
        ]
        urls = load_career_urls(str(workbook), discover=True)

    finder.find.assert_called_once_with("https://example.com", discover=True)
    assert urls[0] == "https://boards.greenhouse.io/example"
    assert "https://example.com/careers" in urls


def test_load_career_urls_skips_company_without_urls(tmp_path):
    workbook = tmp_path / "companies.xlsx"
    pd.DataFrame([{"Company": "Example"}]).to_excel(workbook, index=False)

    assert load_career_urls(str(workbook)) == []


def test_load_career_urls_removes_duplicates(tmp_path):
    workbook = tmp_path / "companies.xlsx"
    pd.DataFrame([
        {"Company": "Example", "Career URL": "https://jobs.lever.co/example"},
        {"Company": "Example", "Career URL": "https://jobs.lever.co/example"},
    ]).to_excel(workbook, index=False)

    assert load_career_urls(str(workbook)) == ["https://jobs.lever.co/example"]


@patch("main.load_resume_skills", return_value=["python", "selenium"])
@patch("main.build_scheduler")
def test_run_once_executes_pipeline(mock_build_scheduler, mock_load_skills, tmp_path):
    scheduler = MagicMock()
    scheduler.run_pipeline.return_value = {
        "sources": 1,
        "jobs_found": 2,
        "jobs_saved": 1,
        "jobs_skipped": 1,
        "notifications_sent": 0,
        "errors": [],
    }
    mock_build_scheduler.return_value = scheduler
    settings = make_settings(tmp_path)

    summary = run_once(["https://example.com/careers"], settings)

    scheduler.run_pipeline.assert_called_once_with(
        career_urls=["https://example.com/careers"],
        resume_skills=["python", "selenium"],
        min_score=60.0,
        notification=None,
    )
    scheduler.database.close.assert_called_once()
    assert summary["jobs_saved"] == 1


@patch("main.load_resume_skills", return_value=["python"])
@patch("main.build_scheduler")
def test_run_scheduled_registers_and_starts_scheduler(
    mock_build_scheduler, mock_load_skills, tmp_path
):
    scheduler = MagicMock()
    mock_build_scheduler.return_value = scheduler
    settings = make_settings(tmp_path, scheduler_hours=3)
    urls = ["https://example.com/careers"]

    run_scheduled(urls, settings)

    scheduler.add_pipeline_job.assert_called_once_with(
        career_urls=urls,
        resume_skills=["python"],
        hours=3,
        min_score=60.0,
        notification=None,
    )
    scheduler.start.assert_called_once()
    scheduler.database.close.assert_called_once()


@patch("main.load_resume_skills", side_effect=FileNotFoundError("resume missing"))
@patch("main.build_scheduler")
def test_run_once_closes_database_when_resume_loading_fails(
    mock_build_scheduler, mock_load_skills, tmp_path
):
    scheduler = MagicMock()
    mock_build_scheduler.return_value = scheduler
    settings = make_settings(tmp_path)

    try:
        run_once(["https://example.com/careers"], settings)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass

    scheduler.database.close.assert_called_once()
