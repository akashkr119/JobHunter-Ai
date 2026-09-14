"""Enforce explicit authorization before application submission."""

from __future__ import annotations

from dataclasses import dataclass

from matcher.application_authorization import (
    ApplicationAuthorization,
    AuthorizationDecision,
)
from matcher.application_package import ApplicationPackage


@dataclass(frozen=True)
class SubmissionPermit:
    """Permit proving that one prepared package was explicitly approved."""

    package: ApplicationPackage
    approval_id: str


def authorize_application_submission(
    authorization: ApplicationAuthorization,
    *,
    approval_id: str,
) -> SubmissionPermit:
    """Return a submission permit only for an explicitly approved request.

    This function does not submit an application or contact an external site.
    """
    normalized_id = str(approval_id).strip()
    if not normalized_id:
        raise ValueError("approval_id is required")
    if authorization.decision is not AuthorizationDecision.APPROVED:
        raise PermissionError("Explicit user approval is required before submission")
    return SubmissionPermit(package=authorization.package, approval_id=normalized_id)
