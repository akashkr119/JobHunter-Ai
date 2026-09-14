"""End-to-end orchestration for explicitly authorized application submission."""

from __future__ import annotations

from matcher.application_authorization import ApplicationAuthorization
from matcher.application_submission import (
    SubmissionAdapter,
    SubmissionExecutor,
    SubmissionResult,
    authorize_application_submission,
)
from matcher.submission_state import SubmissionStateStore


def submit_authorized_application(
    authorization: ApplicationAuthorization,
    *,
    approval_id: str,
    adapter: SubmissionAdapter,
    state_store: SubmissionStateStore | None = None,
) -> SubmissionResult:
    """Run the complete safe submission path for one explicitly approved package.

    Authorization and completeness are checked before the executor can claim
    durable submission state or call the external adapter. The caller remains
    responsible for supplying a supported, authorized transport through the
    adapter; this function performs no browser or authentication automation.
    """
    permit = authorize_application_submission(
        authorization,
        approval_id=approval_id,
    )
    executor = SubmissionExecutor(adapter, state_store)
    try:
        return executor.submit(permit)
    finally:
        executor.close()
