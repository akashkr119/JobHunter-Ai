"""Authorize and execute supported application submissions safely.

The executor is adapter-based. It never bypasses authentication, CAPTCHAs,
or platform restrictions, and it refuses duplicate package execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Protocol

from matcher.application_authorization import ApplicationAuthorization, AuthorizationDecision
from matcher.application_package import ApplicationPackage, missing_required_information
from matcher.submission_state import SubmissionStateStore


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"
    FAILED = "failed"
    NEEDS_USER_INPUT = "needs_user_input"


class SubmissionFailureCategory(str, Enum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"


class RetryableSubmissionError(RuntimeError):
    """An adapter failure that is safe to retry because no submission outcome is known."""


class NonRetryableSubmissionError(RuntimeError):
    """An adapter failure that must be corrected rather than retried automatically."""


@dataclass(frozen=True)
class SubmissionPermit:
    package: ApplicationPackage
    approval_id: str

    @property
    def package_fingerprint(self) -> str:
        return package_fingerprint(self.package)


@dataclass(frozen=True)
class SubmissionResult:
    status: SubmissionStatus
    package_fingerprint: str
    message: str
    failure_category: SubmissionFailureCategory | None = None


class SubmissionAdapter(Protocol):
    """A supported adapter that performs one authorized application flow."""

    def submit(self, package: ApplicationPackage) -> str: ...


def package_fingerprint(package: ApplicationPackage) -> str:
    """Create a stable SHA-256 identity for the exact prepared package."""
    payload = "\n".join(
        (
            package.job_title,
            package.company,
            package.apply_url,
            package.resume_path,
            package.cover_letter,
            *[f"{question}={answer}" for question, answer in package.answers],
            *[f"required={question}" for question in package.required_questions],
            str(package.ready_for_review),
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def authorize_application_submission(
    authorization: ApplicationAuthorization,
    *,
    approval_id: str,
) -> SubmissionPermit:
    """Create a permit only for an approved, complete, review-ready package."""
    normalized_id = str(approval_id).strip()
    if not normalized_id:
        raise ValueError("approval_id is required")
    if authorization.decision is not AuthorizationDecision.APPROVED:
        raise PermissionError("Explicit user approval is required before submission")
    if not authorization.package.ready_for_review:
        raise PermissionError("Application package is not ready for submission")
    missing = missing_required_information(authorization.package)
    if missing:
        raise ValueError(
            "Required application information is missing: " + ", ".join(missing)
        )
    return SubmissionPermit(authorization.package, normalized_id)


class SubmissionExecutor:
    """Execute each exact package at most once with durable idempotency state."""

    def __init__(self, adapter: SubmissionAdapter, state_store: SubmissionStateStore | None = None) -> None:
        self._adapter = adapter
        self._state_store = state_store or SubmissionStateStore()
        self._submitted_fingerprints: set[str] = set()

    def submit(self, permit: SubmissionPermit) -> SubmissionResult:
        fingerprint = permit.package_fingerprint
        missing = missing_required_information(permit.package)
        if missing:
            return SubmissionResult(
                SubmissionStatus.NEEDS_USER_INPUT,
                fingerprint,
                "Required application information is missing: " + ", ".join(missing),
            )
        if fingerprint in self._submitted_fingerprints:
            raise RuntimeError("Application package has already been submitted")

        self._state_store.claim(fingerprint, permit.approval_id)
        try:
            message = self._adapter.submit(permit.package)
        except RetryableSubmissionError as exc:
            self._state_store.mark_failed(fingerprint, str(exc))
            return SubmissionResult(
                SubmissionStatus.FAILED,
                fingerprint,
                str(exc),
                SubmissionFailureCategory.RETRYABLE,
            )
        except NonRetryableSubmissionError as exc:
            self._state_store.mark_failed(fingerprint, str(exc))
            return SubmissionResult(
                SubmissionStatus.FAILED,
                fingerprint,
                str(exc),
                SubmissionFailureCategory.NON_RETRYABLE,
            )
        except Exception as exc:
            self._state_store.mark_failed(fingerprint, str(exc))
            return SubmissionResult(
                SubmissionStatus.FAILED,
                fingerprint,
                str(exc),
                SubmissionFailureCategory.NON_RETRYABLE,
            )

        self._state_store.mark_submitted(fingerprint, str(message))
        self._submitted_fingerprints.add(fingerprint)
        return SubmissionResult(SubmissionStatus.SUBMITTED, fingerprint, str(message))

    def retry(self, permit: SubmissionPermit) -> SubmissionResult:
        """Retry only a persistently failed package; never retry unknown outcomes."""
        fingerprint = permit.package_fingerprint
        state = self._state_store.get(fingerprint)
        if state is None or state.state != "failed":
            raise RuntimeError("Only a failed submission can be explicitly retried")
        if state.approval_id != permit.approval_id:
            raise PermissionError("Submission approval does not match the recorded attempt")
        return self.submit(permit)

    def close(self) -> None:
        self._state_store.close()
