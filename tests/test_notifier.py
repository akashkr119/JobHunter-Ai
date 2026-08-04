"""Unit tests for notifier."""

from unittest.mock import MagicMock, patch

import pytest

from crawler.job_scraper import Job
from notifier.notifier import Notifier


def test_notifier_instance():
    notifier = Notifier()
    assert notifier is not None


def test_has_send_method():
    notifier = Notifier()
    assert hasattr(notifier, "send")


def test_send_method_is_callable():
    notifier = Notifier()
    assert callable(notifier.send)


def test_email_requires_configuration():
    notifier = Notifier()
    with pytest.raises(ValueError, match="SMTP"):
        notifier.send_email("user@example.com", "Job", "Body")


@patch("notifier.notifier.smtplib.SMTP")
def test_send_email_uses_smtp(mock_smtp):
    smtp = MagicMock()
    mock_smtp.return_value.__enter__.return_value = smtp
    notifier = Notifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="bot@example.com",
        smtp_password="secret",
        smtp_sender="jobs@example.com",
    )

    result = notifier.send_email("user@example.com", "New Job", "Apply now")

    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=20)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("bot@example.com", "secret")
    smtp.send_message.assert_called_once()
    assert result["success"] is True
    assert result["channel"] == "email"
    assert result["recipient"] == "user@example.com"


def test_telegram_requires_token():
    notifier = Notifier()
    with pytest.raises(ValueError, match="Telegram bot token"):
        notifier.send_telegram("123", "New job")


@patch("notifier.notifier.request.urlopen")
def test_send_telegram_uses_bot_api(mock_urlopen):
    response = MagicMock()
    response.read.return_value = b'{"ok": true, "result": {"message_id": 42}}'
    mock_urlopen.return_value.__enter__.return_value = response
    notifier = Notifier(telegram_bot_token="test-token")

    result = notifier.send_telegram("12345", "New matching job")

    assert mock_urlopen.called
    assert result == {
        "success": True,
        "channel": "telegram",
        "chat_id": "12345",
        "message_id": 42,
    }


def test_send_dispatches_email():
    notifier = Notifier()
    with patch.object(notifier, "send_email", return_value={"success": True}) as send_email:
        result = notifier.send(
            "email",
            recipient="user@example.com",
            subject="Job",
            body="Body",
        )

    send_email.assert_called_once_with("user@example.com", "Job", "Body")
    assert result["success"] is True


def test_send_dispatches_telegram():
    notifier = Notifier()
    with patch.object(notifier, "send_telegram", return_value={"success": True}) as send_telegram:
        result = notifier.send("telegram", chat_id="123", message="Job")

    send_telegram.assert_called_once_with("123", "Job")
    assert result["success"] is True


def test_unsupported_channel_rejected():
    notifier = Notifier()
    with pytest.raises(ValueError, match="Unsupported notification channel"):
        notifier.send("sms", message="Job")


def test_format_job_alert():
    job = Job(
        title="QA Automation Engineer",
        company="Example",
        location="Bengaluru",
        apply_url="https://example.com/jobs/1",
        description="Python Selenium",
        platform="greenhouse",
    )
    message = Notifier.format_job_alert(
        job,
        {"score": 85, "missing_skills": ["docker"]},
    )

    assert "QA Automation Engineer" in message
    assert "Example" in message
    assert "Bengaluru" in message
    assert "Match: 85%" in message
    assert "Missing skills: docker" in message
    assert "https://example.com/jobs/1" in message
