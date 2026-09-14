"""Tests for the safe submission executor foundation and durable state."""

import pytest

from matcher.application_authorization import decide_application_authorization, request_application_authorization
from matcher.application_package import prepare_application_package
from matcher.application_submission import (
    SubmissionExecutor,
    SubmissionStatus,
    authorize_application_submission,
    package_fingerprint,
)
from matcher.submission_state import SubmissionState, SubmissionStateStore


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


def test_executor_submits_approved_package_once(tmp_path):
    adapter = FakeAdapter()
    store = SubmissionStateStore(tmp_path / "state.db")
    executor = SubmissionExecutor(adapter, store)
    result = executor.submit(permit_for(package()))
    assert result.status is SubmissionStatus.SUBMITTED
    assert result.message == "accepted"
    assert adapter.calls == 1
    assert store.get(result.package_fingerprint).state == SubmissionState.SUBMITTED
    executor.close()


def test_executor_blocks_duplicate_package_before_adapter(tmp_path):
    adapter = FakeAdapter()
    store = SubmissionStateStore(tmp_path / "state.db")
    executor = SubmissionExecutor(adapter, store)
    permit = permit_for(package())
    executor.submit(permit)
    with pytest.raises(RuntimeError, match="already been submitted"):
        executor.submit(permit)
    assert adapter.calls == 1
    executor.close()


def test_persisted_submitted_state_blocks_after_executor_restart(tmp_path):
    state_path = tmp_path / "state.db"
    first_adapter = FakeAdapter()
    first = SubmissionExecutor(first_adapter, SubmissionStateStore(state_path))
    permit = permit_for(package())
    result = first.submit(permit)
    first.close()

    second_adapter = FakeAdapter()
    second = SubmissionExecutor(second_adapter, SubmissionStateStore(state_path))
    with pytest.raises(RuntimeError, match="already been submitted"):
        second.submit(permit)
    assert second_adapter.calls == 0
    assert result.status is SubmissionStatus.SUBMITTED
    second.close()


def test_different_packages_are_not_duplicates(tmp_path):
    adapter = FakeAdapter()
    executor = SubmissionExecutor(adapter, SubmissionStateStore(tmp_path / "state.db"))
    executor.submit(permit_for(package()))
    result = executor.submit(permit_for(package(cover_letter="Different truthful letter")))
    assert result.status is SubmissionStatus.SUBMITTED
    assert adapter.calls == 2
    executor.close()


def test_failed_submission_is_retryable(tmp_path):
    class FailingAdapter:
        def __init__(self):
            self.calls = 0

        def submit(self, application):
            self.calls += 1
            raise RuntimeError("temporary failure")

    adapter = FailingAdapter()
    executor = SubmissionExecutor(adapter, SubmissionStateStore(tmp_path / "state.db"))
    first = executor.submit(permit_for(package()))
    second = executor.submit(permit_for(package()))
    assert first.status is SubmissionStatus.FAILED
    assert second.status is SubmissionStatus.FAILED
    assert adapter.calls == 2
    executor.close()


def test_failed_submission_is_retryable_after_restart(tmp_path):
    class FailingAdapter:
        def __init__(self):
            self.calls = 0

        def submit(self, application):
            self.calls += 1
            raise RuntimeError("temporary failure")

    state_path = tmp_path / "state.db"
    first_adapter = FailingAdapter()
    first = SubmissionExecutor(first_adapter, SubmissionStateStore(state_path))
    permit = permit_for(package())
    result = first.submit(permit)
    first.close()

    second_adapter = FakeAdapter("accepted on retry")
    second = SubmissionExecutor(second_adapter, SubmissionStateStore(state_path))
    retry = second.submit(permit)
    assert result.status is SubmissionStatus.FAILED
    assert retry.status is SubmissionStatus.SUBMITTED
    assert second_adapter.calls == 1
    second.close()


def test_unresolved_in_progress_state_blocks_after_restart(tmp_path):
    state_path = tmp_path / "state.db"
    store = SubmissionStateStore(state_path)
    permit = permit_for(package())
    store.claim(permit.package_fingerprint, permit.approval_id)
    store.close()

    adapter = FakeAdapter()
    executor = SubmissionExecutor(adapter, SubmissionStateStore(state_path))
    with pytest.raises(RuntimeError, match="unresolved submission attempt"):
        executor.submit(permit)
    assert adapter.calls == 0
    executor.close()


def test_pending_authorization_never_reaches_adapter(tmp_path):
    adapter = FakeAdapter()
    authorization = request_application_authorization(package())
    with pytest.raises(PermissionError):
        authorize_application_submission(authorization, approval_id="approval-1")
    assert adapter.calls == 0
