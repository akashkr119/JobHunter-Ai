"""Build a reviewable application package without submitting it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ApplicationPackage:
    """Structured application data prepared for explicit user review."""

    job_title: str
    company: str
    apply_url: str
    resume_path: str
    cover_letter: str
    answers: tuple[tuple[str, str], ...]
    ready_for_review: bool = True


def prepare_application_package(
    *,
    job_title: str,
    company: str,
    apply_url: str,
    resume_path: str,
    cover_letter: str = "",
    answers: Mapping[str, str] | None = None,
) -> ApplicationPackage:
    """Prepare application data; this function never submits an application."""
    values = {
        "job_title": job_title,
        "company": company,
        "apply_url": apply_url,
        "resume_path": resume_path,
    }
    for name, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must not be empty")

    normalized_answers = tuple(
        (str(question).strip(), str(answer).strip())
        for question, answer in (answers or {}).items()
        if str(question).strip()
    )

    return ApplicationPackage(
        job_title=job_title.strip(),
        company=company.strip(),
        apply_url=apply_url.strip(),
        resume_path=resume_path.strip(),
        cover_letter=cover_letter.strip(),
        answers=normalized_answers,
    )
