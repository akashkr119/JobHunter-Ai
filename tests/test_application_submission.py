"""Tests for the explicit application submission gate."""

import pytest

from matcher.application_authorization import (
    decide_application_authorization,
    request_application_authorization,
)
from matcher.application_package import prepare_application_package
from matcher.application_submission import authorize_application_submission


def package():
    return prepare_application_package(
        job_title="Software Engineer",
        company="Example Co",
        apply_url="https://example.com/apply",
        resume_path="resume.pdf",
    )


def test_pending_authorization_cannot_submit():
    authorization = request_application_authorization(package())
    with pytest.raises(PermissionError, match="Explicit user approval"):
        authorize_application_submission(authorization, approval_id="approval-1")


def test_rejected_authorization_cannot_submit():
    authorization = decide_application_authorization(
        request_application_authorization(package()), "rejected"
    )
    with pytest.raises(PermissionError, match="Explicit user approval"):
        authorize_application_submission(authorization, approval_id="approval-1")


def test_approved_authorization_creates_permit_only():
    authorization = decide_application_authorization(
        request_application_authorization(package()), "approved"
    )
    permit = authorize_application_submission(authorization, approval_id="approval-1")

    assert permit.approval_id == "approval-1"
    assert permit.package is authorization.package


def test_approval_id_is_required():
    authorization = decide_application_authorization(
        request_application_authorization(package()), "approved"
    )
    with pytest.raises(ValueError, match="approval_id"):
        authorize_application_submission(authorization, approval_id=" ")
