"""Tests for the JobHunter application entry point."""

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from main import build_scheduler, load_resume_skills, parse_args, run_once, validate_startup


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


def test_build_scheduler_registers_configured_sources(tmp_path):
    settings = make_settings(
        tmp_path,
        adzuna_app_id="app-id",
        adzuna_app_key="app-key",
        jooble_api_key="jooble-key",
    )
    scheduler = build_scheduler(settings)
    try:
        assert set(scheduler.source_manager.names()) == {"adzuna", "jooble"}
    finally:
        scheduler.database.close()


def test_load_resume_skills(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python Selenium Pytest Docker", encoding="utf-8")
    skills = load_resume_skills(make_settings(tmp_path))
    assert {"python", "selenium", "pytest", "docker"}.issubset(skills)


def test_parse_args_no_longer_accepts_excel_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["jobhunter"])
    args = parse_args()
    assert args.career_urls == []
    assert not hasattr(args, "companies")


def test_validate_startup_accepts_career_url_without_excel(tmp_path):
    settings = make_settings(tmp_path)
    resume = tmp_path / "resume.txt"
    resume.write_text("Python", encoding="utf-8")
    validate_startup(["https://example.com/careers"], settings)


def test_validate_startup_accepts_api_source_without_career_url(tmp_path):
    settings = make_settings(
        tmp_path,
        adzuna_app_id="app-id",
        adzuna_app_key="app-key",
    )
    resume = tmp_path / "resume.txt"
    resume.write_text("Python", encoding="utf-8")
    validate_startup([], settings)


def test_validate_startup_rejects_no_source_configuration(tmp_path):
    settings = make_settings(tmp_path)
    resume = tmp_path / "resume.txt"
    resume.write_text("Python", encoding="utf-8")
    with pytest.raises(ValueError, match="No job sources configured"):
        validate_startup([], settings)


@patch("main.load_resume_skills", return_value=["python", "selenium"])
@patch("main.build_scheduler")
def test_run_once_executes_direct_pipeline(mock_build_scheduler, mock_load_skills, tmp_path):
    scheduler = MagicMock()
    scheduler.source_manager.names.return_value = ()
    scheduler.run_pipeline.return_value = {
        "sources": 1,
        "jobs_found": 2,
        "jobs_saved": 1,
        "jobs_skipped": 1,
        "jobs_preference_excluded": 0,
        "notifications_sent": 0,
        "notifications_suppressed": 0,
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
        preferences=settings.job_preferences(),
    )
    scheduler.database.close.assert_called_once()
    assert summary["jobs_saved"] == 1


@patch("main.process_source_jobs")
@patch("main.load_resume_skills", return_value=["python"])
@patch("main.build_scheduler")
def test_run_once_executes_configured_sources(
    mock_build_scheduler, mock_load_skills, mock_process_source_jobs, tmp_path
):
    scheduler = MagicMock()
    scheduler.source_manager.names.return_value = ("adzuna", "jooble")
    scheduler.run_pipeline.return_value = {
        "sources": 0,
        "jobs_found": 0,
        "jobs_saved": 0,
        "jobs_skipped": 0,
        "jobs_preference_excluded": 0,
        "notifications_sent": 0,
        "notifications_suppressed": 0,
        "errors": [],
    }
    mock_process_source_jobs.side_effect = [
        {"jobs_found": 2, "jobs_saved": 1, "jobs_skipped": 1, "jobs_preference_excluded": 0, "notifications_sent": 0, "notifications_suppressed": 0, "errors": []},
        {"jobs_found": 3, "jobs_saved": 2, "jobs_skipped": 1, "jobs_preference_excluded": 0, "notifications_sent": 0, "notifications_suppressed": 0, "errors": []},
    ]
    mock_build_scheduler.return_value = scheduler
    settings = make_settings(tmp_path)

    summary = run_once([], settings)

    assert mock_process_source_jobs.call_count == 2
    assert summary["jobs_found"] == 5
    assert summary["jobs_saved"] == 3
    assert summary["source_count"] == 2
    scheduler.database.close.assert_called_once()


@patch("main.ProductionRunner")
@patch("main.load_resume_skills", return_value=["python"])
@patch("main.build_scheduler")
def test_run_scheduled_registers_and_starts_scheduler(
    mock_build_scheduler, mock_load_skills, mock_runner, tmp_path
):
    scheduler = MagicMock()
    mock_build_scheduler.return_value = scheduler
    settings = make_settings(tmp_path, scheduler_hours=3)
    urls = ["https://example.com/careers"]
    run_scheduled(urls, settings)
    mock_runner.assert_called_once_with(scheduler, urls, ["python"], settings)
    mock_runner.return_value.start.assert_called_once_with()


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
