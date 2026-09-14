"""End-to-end validation for the safe authorized submission workflow."""

import pytest

from matcher.application_authorization import (
    AuthorizationDecision,
    decide_application_authorization,
    request_application_authorization,
)
from matcher.application_package import prepare_application_package
from matcher.ats_adapters import (
    GreenhouseAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
    WorkdayAdapter,
)
from matcher.submission_state import SubmissionStateStore
from matcher.submission_workflow import submit_authorized_application


def package(url="https://boards.greenhouse.io/example/jobs/123", required_questions=(), answers=None):
    return prepare_application_package(
        job_title="Software Engineer",
        company="Example Co",
        apply_url=url,
        resume_path="resume.pdf",
        required_questions=required_questions,
        answers=answers,
    )


def approved(package_value):
    pending = request_application_authorization(package_value, requested_at="2026-09-14T00:00:00+00:00")
    return decide_application_authorization(
        pending,
        AuthorizationDecision.APPROVED,
        decided_at="2026-09-14T00:01:00+00:00",
    )


@pytest.mark.parametrize(
    ("adapter", "url"),
    [
        (GreenhouseAdapter, "https://boards.greenhouse.io/example/jobs/123"),
        (LeverAdapter, "https://jobs.lever.co/example/123"),
        (WorkdayAdapter, "https://example.myworkdayjobs.com/en-US/Careers/job/123"),
        (SmartRecruitersAdapter, "https://jobs.smartrecruiters.com/Example/123"),
    ],
)
def test_end_to_end_approved_package_reaches_supported_ats_transport(tmp_path, adapter, url):
    calls = []
    store = SubmissionStateStore(tmp_path / "state.db")
    try:
        result = submit_authorized_application(
            approved(package(url)),
            approval_id="approval-14-12",
            adapter=adapter(lambda application: calls.append(application) or "external-id-123"),
            state_store=store,
        )

        assert result.status.value == "submitted"
        assert result.message == "external-id-123"
        assert len(calls) == 1
        assert calls[0].apply_url == url
        assert store.get(result.package_fingerprint).state == "submitted"
    finally:
        store.close()


def test_pending_authorization_never_calls_transport_or_claims_state(tmp_path):
    calls = []
    application = request_application_authorization(package(), requested_at="2026-09-14T00:00:00+00:00")
    store = SubmissionStateStore(tmp_path / "state.db")
    try:
        with pytest.raises(PermissionError, match="Explicit user approval"):
            submit_authorized_application(
                application,
                approval_id="approval-14-12",
                adapter=GreenhouseAdapter(lambda value: calls.append(value) or "must-not-submit"),
                state_store=store,
            )
        assert calls == []
        assert list(store.conn.execute("SELECT * FROM submission_state")) == []
    finally:
        store.close()


def test_missing_required_information_never_calls_transport_or_claims_state(tmp_path):
    calls = []
    application = approved(package(required_questions=("Work authorization",), answers={"Work authorization": ""}))
    store = SubmissionStateStore(tmp_path / "state.db")
    try:
        with pytest.raises(ValueError, match="Required application information is missing"):
            submit_authorized_application(
                application,
                approval_id="approval-14-12",
                adapter=GreenhouseAdapter(lambda value: calls.append(value) or "must-not-submit"),
                state_store=store,
            )
        assert calls == []
        assert list(store.conn.execute("SELECT * FROM submission_state")) == []
    finally:
        store.close()


def test_duplicate_end_to_end_submission_is_blocked(tmp_path):
    calls = []
    application = approved(package())
    store = SubmissionStateStore(tmp_path / "state.db")
    try:
        adapter = GreenhouseAdapter(lambda value: calls.append(value) or "external-id-123")
        first = submit_authorized_application(
            application,
            approval_id="approval-14-12",
            adapter=adapter,
            state_store=store,
        )
        with pytest.raises(RuntimeError, match="already been submitted"):
            submit_authorized_application(
                application,
                approval_id="approval-14-12",
                adapter=adapter,
                state_store=store,
            )
        assert first.status.value == "submitted"
        assert len(calls) == 1
    finally:
        store.close()
