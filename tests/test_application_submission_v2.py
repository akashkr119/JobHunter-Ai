"""Tests for safe submission execution primitives."""

import pytest

from matcher.application_authorization import (
    decide_application_authorization,
    request_application_authorization,
)
from matcher.application_package import prepare_application_package
from matcher.application_submission_v2 import (
    SubmissionExecutor,
    SubmissionStatus,
    authorize_application_submission,
    package_fingerprint,
)


def package():
    return prepare_application_package(
        job_title="Software Engineer",
        company="Example Co",
        apply_url="https://example.com/apply",
        resume_path="resume.pdf",
    )


class FakeAdapter:
    def __init__(self, result="submitted"):
        self.calls = 0
        self.result = result

    def submit(self, application):
        self.calls += 1
        return self.result


def approved_permit():
    authorization = decide_application_authorization(
        request_application_authorization(package()), "approved"
    )
    return authorize_application_submission(authorization, approval_id="approval-1")


def test_fingerprint_changes_when_package_changes():
    original = package()
    changed = prepare_application_package(
        job_title=original.job_title,
        company=original.company,
        apply_url=original.apply_url,
        resume_path=original.resume_path,
        cover_letter="Truthful cover letter",
    )
    assert package_fingerprint(original) != package_fingerprint(changed)


def test_executor_submits_approved_package_once():
    adapter = FakeAdapter()
    result = SubmissionExecutor(adapter).submit(approved_permit())
    assert result.status is SubmissionStatus.SUBMITTED
    assert adapter.calls == 1


def test_executor_blocks_duplicate_package_before_adapter():
    adapter = FakeAdapter()
    executor = SubmissionExecutor(adapter)
    permit = approved_permit()
    executor.submit(permit)
    with pytest.raises(RuntimeError, match="already been submitted"):
        executor.submit(permit)
    assert adapter.calls == 1


def test_failed_submission_is_not_marked_as_submitted():
    class FailingAdapter:
        calls = 0

        def submit(self, application):
            self.calls += 1
            raise RuntimeError("temporary failure")

    adapter = FailingAdapter()
    executor = SubmissionExecutor(adapter)
    first = executor.submit(approved_permit())
    second = executor.submit(approved_permit())
    assert first.status is SubmissionStatus.FAILED
    assert second.status is SubmissionStatus.FAILED
    assert adapter.calls == 2


def test_pending_authorization_never_reaches_adapter():
    adapter = FakeAdapter()
    executor = SubmissionExecutor(adapter)
    authorization = request_application_authorization(package())
    with pytest.raises(PermissionError):
        permit = authorize_application_submission(authorization, approval_id="approval-1")
        executor.submit(permit)
    assert adapter.calls == 0
