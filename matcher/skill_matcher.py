"""Utilities for matching resume skills against job requirements."""

import re
from collections.abc import Iterable

from matcher.resume_parser import ResumeParser


class SkillMatcher:
    """Score resume skills against job requirements and rank job matches."""

    def __init__(self, skill_catalog: Iterable[str] | None = None) -> None:
        self.skill_catalog = tuple(skill_catalog or ResumeParser.DEFAULT_SKILLS)

    def extract_job_skills(self, job_description: str) -> list[str]:
        """Extract known skills from a job description."""
        parser = ResumeParser()
        return parser.extract_skills(job_description or "", self.skill_catalog)

    def match(
        self,
        resume_skills: Iterable[str],
        job_skills: Iterable[str] | None = None,
        job_description: str | None = None,
    ) -> dict:
        """Return a deterministic skill-match score and supporting details.

        ``job_skills`` can be supplied directly. If omitted, skills are
        extracted from ``job_description`` using the shared skill catalog.
        """
        resume = self._normalize_skills(resume_skills)

        if job_skills is None:
            job_skills = self.extract_job_skills(job_description or "")
        job = self._normalize_skills(job_skills)

        matched = sorted(resume & job)
        missing = sorted(job - resume)
        extra = sorted(resume - job)
        score = round((len(matched) / len(job)) * 100, 2) if job else 0.0

        return {
            "score": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "resume_only_skills": extra,
            "resume_skill_count": len(resume),
            "job_skill_count": len(job),
            "matched_skill_count": len(matched),
        }

    def match_job(self, resume_skills: Iterable[str], job) -> dict:
        """Score a normalized Job object or job dictionary."""
        if isinstance(job, dict):
            description = job.get("description", "")
            title = job.get("title", "")
            company = job.get("company", "")
            apply_url = job.get("apply_url", "")
        else:
            description = getattr(job, "description", "")
            title = getattr(job, "title", "")
            company = getattr(job, "company", "")
            apply_url = getattr(job, "apply_url", "")

        result = self.match(resume_skills, job_description=description)
        result.update(
            {
                "title": title,
                "company": company,
                "apply_url": apply_url,
            }
        )
        return result

    def rank_jobs(self, resume_skills: Iterable[str], jobs: Iterable) -> list[dict]:
        """Rank jobs from highest to lowest skill-match score."""
        results = [self.match_job(resume_skills, job) for job in jobs]
        return sorted(
            results,
            key=lambda item: (
                -item["score"],
                str(item.get("company", "")).lower(),
                str(item.get("title", "")).lower(),
            ),
        )

    @staticmethod
    def _normalize_skills(skills: Iterable[str] | None) -> set[str]:
        """Normalize skill names for case-insensitive comparison."""
        if not skills:
            return set()

        normalized: set[str] = set()
        for skill in skills:
            value = re.sub(r"\s+", " ", str(skill or "").strip().lower())
            if value:
                normalized.add(value)
        return normalized
