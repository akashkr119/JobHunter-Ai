"""Deterministic resume-to-job skill gap analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from matcher.resume_parser import ResumeParser


@dataclass(frozen=True)
class ResumeGapAnalysis:
    """Skills present in a resume and skills detected as missing from it."""

    resume_skills: tuple[str, ...]
    job_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    matched_skills: tuple[str, ...]

    @property
    def match_ratio(self) -> float:
        """Return the fraction of detected job skills covered by the resume."""
        if not self.job_skills:
            return 1.0
        return len(self.matched_skills) / len(self.job_skills)


def analyze_resume_gap(
    resume: str | dict | Iterable[str],
    job_description: str,
    *,
    skills: Iterable[str] | None = None,
) -> ResumeGapAnalysis:
    """Compare resume skills with skills detected in a job description.

    ``resume`` may be parsed resume data, raw resume text, or an iterable of
    already-normalized skills. The function only reports detected gaps; it
    never invents qualifications or modifies the resume.
    """
    parser = ResumeParser()
    candidates = tuple(skills) if skills is not None else parser.DEFAULT_SKILLS

    if isinstance(resume, dict):
        resume_skills = tuple(
            parser._normalize(skill)
            for skill in resume.get("skills", ())
            if parser._normalize(skill)
        )
    elif isinstance(resume, str):
        resume_skills = tuple(parser.extract_skills(resume, list(candidates)))
    else:
        resume_skills = tuple(
            parser._normalize(skill)
            for skill in resume
            if parser._normalize(skill)
        )

    job_skills = tuple(parser.extract_skills(job_description, list(candidates)))
    resume_set = set(resume_skills)
    matched = tuple(skill for skill in job_skills if skill in resume_set)
    missing = tuple(skill for skill in job_skills if skill not in resume_set)

    return ResumeGapAnalysis(
        resume_skills=resume_skills,
        job_skills=job_skills,
        missing_skills=missing,
        matched_skills=matched,
    )
