"""Tests for review-only application approval notifications."""

import pytest

from matcher.application_approval import build_approval_notification
from matcher.application_authorization import request_application_authorization
from matcher.application_package import prepare_application_package


def package():
    return prepare_application_package(
        job_title="Software Engineer",
        company="Example Co",
        apply_url="https://example.com/apply",
        resume_path="resume.pdf",
    )


def test_builds_pending_approval_notification():
    authorization = request_application_authorization(package(), requested_at="2026-09-14T10:00:00+00:00")
    notification = build_approval_notification(authorization, approval_id="approval-1")

    assert notification.approval_id == "approval-1"
    assert "Approval Required" in notification.subject
    assert "Software Engineer" in notification.body
    assert "Example Co" in notification.body
    assert "APPROVE / REVIEW / REJECT" in notification.body
    assert authorization.decision.value == "pending"
    assert authorization.can_submit is False


def test_approval_id_is_required():
    authorization = request_application_authorization(package())
    with pytest.raises(ValueError, match="approval_id"):
        build_approval_notification(authorization, approval_id=" ")


def test_approved_authorization_cannot_create_pending_request():
    from matcher.application_authorization import decide_application_authorization

    authorization = request_application_authorization(package())
    approved = decide_application_authorization(authorization, "approved")
    with pytest.raises(ValueError, match="pending authorization"):
        build_approval_notification(approved, approval_id="approval-2")
