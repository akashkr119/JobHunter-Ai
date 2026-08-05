"""Unit tests for centralized JobHunter settings."""

import pytest

from config.settings import DATABASE_PATH, Settings

ENV_KEYS=["JOBHUNTER_DATABASE_PATH","JOBHUNTER_RESUME_PATH","JOBHUNTER_MIN_MATCH_SCORE","JOBHUNTER_SCHEDULER_HOURS","JOBHUNTER_SMTP_HOST","JOBHUNTER_SMTP_PORT","JOBHUNTER_SMTP_USERNAME","JOBHUNTER_SMTP_PASSWORD","JOBHUNTER_SMTP_SENDER","JOBHUNTER_EMAIL_RECIPIENT","JOBHUNTER_TELEGRAM_BOT_TOKEN","JOBHUNTER_TELEGRAM_CHAT_ID","JOBHUNTER_NOTIFICATION_CHANNEL","JOBHUNTER_NOTIFICATION_MIN_PRIORITY"]

def clear_jobhunter_env(monkeypatch):
    for key in ENV_KEYS:monkeypatch.delenv(key,raising=False)

def test_settings_defaults(monkeypatch):
    clear_jobhunter_env(monkeypatch);settings=Settings.from_env();assert settings.database_path==str(DATABASE_PATH);assert settings.resume_path=="resume.pdf";assert settings.min_match_score==60.0;assert settings.scheduler_hours==6;assert settings.smtp_port==587;assert settings.notification_channel is None;assert settings.notification_min_priority=="apply_now"
def test_environment_overrides(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH","custom.db");monkeypatch.setenv("JOBHUNTER_RESUME_PATH","my_resume.docx");monkeypatch.setenv("JOBHUNTER_MIN_MATCH_SCORE","75.5");monkeypatch.setenv("JOBHUNTER_SCHEDULER_HOURS","2");monkeypatch.setenv("JOBHUNTER_SMTP_PORT","465");monkeypatch.setenv("JOBHUNTER_NOTIFICATION_MIN_PRIORITY","HIGH");settings=Settings.from_env();assert settings.database_path=="custom.db";assert settings.resume_path=="my_resume.docx";assert settings.min_match_score==75.5;assert settings.scheduler_hours==2;assert settings.smtp_port==465;assert settings.notification_min_priority=="high"
def test_invalid_match_score_rejected(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_MIN_MATCH_SCORE","101")
    with pytest.raises(ValueError,match="MIN_MATCH_SCORE"):Settings.from_env()
def test_invalid_scheduler_interval_rejected(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_SCHEDULER_HOURS","0")
    with pytest.raises(ValueError,match="SCHEDULER_HOURS"):Settings.from_env()
def test_invalid_integer_environment_value(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_SMTP_PORT","invalid")
    with pytest.raises(ValueError,match="SMTP_PORT must be an integer"):Settings.from_env()
def test_invalid_notification_channel_rejected(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_NOTIFICATION_CHANNEL","sms")
    with pytest.raises(ValueError,match="NOTIFICATION_CHANNEL"):Settings.from_env()
def test_invalid_notification_priority_rejected(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_NOTIFICATION_MIN_PRIORITY","urgent")
    with pytest.raises(ValueError,match="NOTIFICATION_MIN_PRIORITY"):Settings.from_env()
def test_telegram_notification_config(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_NOTIFICATION_CHANNEL","telegram");monkeypatch.setenv("JOBHUNTER_TELEGRAM_BOT_TOKEN","token");monkeypatch.setenv("JOBHUNTER_TELEGRAM_CHAT_ID","12345");settings=Settings.from_env();assert settings.notification_config()=={"channel":"telegram","chat_id":"12345","minimum_priority":"apply_now"}
def test_telegram_notification_priority_override(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_NOTIFICATION_CHANNEL","telegram");monkeypatch.setenv("JOBHUNTER_TELEGRAM_BOT_TOKEN","token");monkeypatch.setenv("JOBHUNTER_TELEGRAM_CHAT_ID","12345");monkeypatch.setenv("JOBHUNTER_NOTIFICATION_MIN_PRIORITY","medium");assert Settings.from_env().notification_config()["minimum_priority"]=="medium"
def test_telegram_notification_requires_credentials(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_NOTIFICATION_CHANNEL","telegram");settings=Settings.from_env()
    with pytest.raises(ValueError,match="Telegram notification"):settings.notification_config()
def test_email_notification_config(monkeypatch):
    clear_jobhunter_env(monkeypatch);monkeypatch.setenv("JOBHUNTER_NOTIFICATION_CHANNEL","email");monkeypatch.setenv("JOBHUNTER_SMTP_HOST","smtp.example.com");monkeypatch.setenv("JOBHUNTER_SMTP_SENDER","jobs@example.com");monkeypatch.setenv("JOBHUNTER_EMAIL_RECIPIENT","user@example.com");settings=Settings.from_env();assert settings.notification_config()=={"channel":"email","recipient":"user@example.com","minimum_priority":"apply_now"}
def test_disabled_notifications_return_none(monkeypatch):clear_jobhunter_env(monkeypatch);assert Settings.from_env().notification_config() is None
