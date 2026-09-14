"""Build a reviewable application package without submitting it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ApplicationPackage:
    """Structured application data prepared for explicit user review."""

    job_title: str
    company: str
    apply_url: str
    resume_path: str
    cover_letter: str
    answers: tuple[tuple[str, str], ...]
    required_questions: tuple[str, ...] = ()
    ready_for_review: bool = True


def prepare_application_package(
    *,
    job_title: str,
    company: str,
    apply_url: str,
    resume_path: str,
    cover_letter: str = "",
    answers: Mapping[str, str] | None = None,
    required_questions: Iterable[str] = (),
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
    normalized_required = tuple(
        str(question).strip()
        for question in required_questions
        if str(question).strip()
    )
    if len(set(normalized_required)) != len(normalized_required):
        raise ValueError("required_questions must not contain duplicates")

    return ApplicationPackage(
        job_title=job_title.strip(),
        company=company.strip(),
        apply_url=apply_url.strip(),
        resume_path=resume_path.strip(),
        cover_letter=cover_letter.strip(),
        answers=normalized_answers,
        required_questions=normalized_required,
    )


def missing_required_information(package: ApplicationPackage) -> tuple[str, ...]:
    """Return required application questions that have no truthful user answer."""
    answers = dict(package.answers)
    return tuple(
        question for question in package.required_questions
        if not answers.get(question, "").strip()
    )
