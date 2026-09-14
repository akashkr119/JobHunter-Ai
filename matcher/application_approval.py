"""Build review-only application approval notifications."""

from __future__ import annotations

from dataclasses import dataclass

from matcher.application_authorization import ApplicationAuthorization


@dataclass(frozen=True)
class ApprovalNotification:
    """Notification content for one pending application authorization."""

    subject: str
    body: str
    approval_id: str
    actions: tuple[str, ...] = ("approve", "reject", "review")


def build_approval_notification(
    authorization: ApplicationAuthorization,
    *,
    approval_id: str,
) -> ApprovalNotification:
    """Build an approval request without approving or submitting anything."""
    if not str(approval_id).strip():
        raise ValueError("approval_id is required")
    if not authorization.package.ready_for_review:
        raise ValueError("Application package must be ready for review")
    if authorization.can_submit:
        raise ValueError("Approval notification requires a pending authorization")

    package = authorization.package
    title = f"{package.job_title} — {package.company}".strip(" —")
    body = "\n".join(
        (
            "Application Approval Required",
            "",
            f"Job: {title}",
            f"Resume: {package.resume_path}",
            f"Apply: {package.apply_url}",
            "",
            "The application is prepared and ready for your review.",
            "No application will be submitted until you explicitly approve this request.",
            "",
            "Actions: APPROVE / REVIEW / REJECT",
        )
    )
    return ApprovalNotification(
        subject=f"JobHunter AI: Approval Required — {title}",
        body=body,
        approval_id=str(approval_id).strip(),
    )
