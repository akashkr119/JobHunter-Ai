"""Tests for the safe submission executor foundation."""

import pytest

from matcher.application_authorization import decide_application_authorization, request_application_authorization
from matcher.application_package import prepare_application_package
from matcher.application_submission import (
    SubmissionExecutor,
    SubmissionStatus,
    authorize_application_submission,
    package_fingerprint,
)


def package(**kwargs):
    values = dict(
        job_title="Software Engineer",
        company="Example Co",
        apply_url="https://example.com/apply",
        resume_path="resume.pdf",
    )
    values.update(kwargs)
    return prepare_application_package(**values)


class FakeAdapter:
    def __init__(self, result="accepted"):
        self.calls = 0
        self.result = result

    def submit(self, application):
        self.calls += 1
        return self.result


def permit_for(application):
    authorization = decide_application_authorization(
        request_application_authorization(application), "approved"
    )
    return authorize_application_submission(authorization, approval_id="approval-1")


def test_fingerprint_changes_when_package_changes():
    assert package_fingerprint(package()) != package_fingerprint(
        package(cover_letter="Truthful cover letter")
    )


def test_executor_submits_approved_package_once():
    adapter = FakeAdapter()
    result = SubmissionExecutor(adapter).submit(permit_for(package()))
    assert result.status is SubmissionStatus.SUBMITTED
    assert result.message == "accepted"
    assert adapter.calls == 1


def test_executor_blocks_duplicate_package_before_adapter():
    adapter = FakeAdapter()
    executor = SubmissionExecutor(adapter)
    permit = permit_for(package())
    executor.submit(permit)
    with pytest.raises(RuntimeError, match="already been submitted"):
        executor.submit(permit)
    assert adapter.calls == 1


def test_different_packages_are_not_duplicates():
    adapter = FakeAdapter()
    executor = SubmissionExecutor(adapter)
    executor.submit(permit_for(package()))
    result = executor.submit(permit_for(package(cover_letter="Different truthful letter")))
    assert result.status is SubmissionStatus.SUBMITTED
    assert adapter.calls == 2


def test_failed_submission_is_retryable():
    class FailingAdapter:
        def __init__(self):
            self.calls = 0

        def submit(self, application):
            self.calls += 1
            raise RuntimeError("temporary failure")

    adapter = FailingAdapter()
    executor = SubmissionExecutor(adapter)
    first = executor.submit(permit_for(package()))
    second = executor.submit(permit_for(package()))
    assert first.status is SubmissionStatus.FAILED
    assert second.status is SubmissionStatus.FAILED
    assert adapter.calls == 2


def test_pending_authorization_never_reaches_adapter():
    adapter = FakeAdapter()
    authorization = request_application_authorization(package())
    with pytest.raises(PermissionError):
        authorize_application_submission(authorization, approval_id="approval-1")
    assert adapter.calls == 0
