from matcher.application_authorization import (
    AuthorizationDecision,
    decide_application_authorization,
    request_application_authorization,
)
from matcher.application_package import prepare_application_package


def package():
    return prepare_application_package(
        job_title="Software Engineer",
        company="Example Corp",
        apply_url="https://example.com/apply",
        resume_path="resume.pdf",
    )


def test_request_starts_pending_and_cannot_submit():
    authorization = request_application_authorization(package(), requested_at="2026-09-14T10:00:00+00:00")
    assert authorization.decision is AuthorizationDecision.PENDING
    assert authorization.can_submit is False
    assert authorization.requested_at == "2026-09-14T10:00:00+00:00"


def test_explicit_approval_allows_submission_state():
    authorization = request_application_authorization(package(), requested_at="requested")
    approved = decide_application_authorization(authorization, "approved", decided_at="approved")
    assert approved.decision is AuthorizationDecision.APPROVED
    assert approved.can_submit is True
    assert approved.decided_at == "approved"


def test_rejection_never_allows_submission():
    authorization = request_application_authorization(package())
    rejected = decide_application_authorization(authorization, AuthorizationDecision.REJECTED)
    assert rejected.decision is AuthorizationDecision.REJECTED
    assert rejected.can_submit is False


def test_pending_cannot_be_recorded_as_a_decision():
    authorization = request_application_authorization(package())
    try:
        decide_application_authorization(authorization, "pending")
    except ValueError as exc:
        assert "approved or rejected" in str(exc)
    else:
        raise AssertionError("pending must not authorize an application")


def test_invalid_decision_is_rejected():
    authorization = request_application_authorization(package())
    try:
        decide_application_authorization(authorization, "submit")
    except ValueError as exc:
        assert "approved or rejected" in str(exc)
    else:
        raise AssertionError("invalid decision must fail")
