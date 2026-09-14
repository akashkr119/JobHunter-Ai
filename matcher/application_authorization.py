"""Manage explicit user authorization for application submission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from matcher.application_package import ApplicationPackage


class AuthorizationDecision(str, Enum):
    """Possible user decisions for a prepared application."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ApplicationAuthorization:
    """Review state tied to one immutable application package."""

    package: ApplicationPackage
    decision: AuthorizationDecision = AuthorizationDecision.PENDING
    requested_at: str = ""
    decided_at: str = ""

    @property
    def can_submit(self) -> bool:
        """Return true only after explicit approval of this package."""
        return self.decision is AuthorizationDecision.APPROVED


def request_application_authorization(
    package: ApplicationPackage,
    *,
    requested_at: str | None = None,
) -> ApplicationAuthorization:
    """Create a pending authorization request without submitting anything."""
    if not package.ready_for_review:
        raise ValueError("Application package must be ready for review")
    timestamp = requested_at or datetime.now(timezone.utc).isoformat()
    return ApplicationAuthorization(package=package, requested_at=timestamp)


def decide_application_authorization(
    authorization: ApplicationAuthorization,
    decision: AuthorizationDecision | str,
    *,
    decided_at: str | None = None,
) -> ApplicationAuthorization:
    """Record an explicit approve/reject decision for the same package."""
    try:
        normalized = (
            decision
            if isinstance(decision, AuthorizationDecision)
            else AuthorizationDecision(str(decision).strip().lower())
        )
    except ValueError as exc:
        raise ValueError("Decision must be 'approved' or 'rejected'") from exc
    if normalized is AuthorizationDecision.PENDING:
        raise ValueError("A decision must be approved or rejected")
    timestamp = decided_at or datetime.now(timezone.utc).isoformat()
    return ApplicationAuthorization(
        package=authorization.package,
        decision=normalized,
        requested_at=authorization.requested_at,
        decided_at=timestamp,
    )
