"""Utilities for matching resume skills against job requirements."""

import re
from collections.abc import Iterable

from matcher.resume_parser import ResumeParser


class SkillMatcher:
    """Score resume skills against job requirements and rank job matches."""

    REQUIRED_MARKERS = (
        "required", "requirements", "must have", "must-have", "mandatory",
        "minimum qualifications", "what you need", "you have",
    )
    PREFERRED_MARKERS = (
        "preferred", "nice to have", "nice-to-have", "bonus", "desired",
        "good to have", "preferred qualifications",
    )

    def __init__(self, skill_catalog: Iterable[str] | None = None) -> None:
        self.skill_catalog = tuple(skill_catalog or ResumeParser.DEFAULT_SKILLS)

    def extract_job_skills(self, job_description: str) -> list[str]:
        return ResumeParser().extract_skills(job_description or "", self.skill_catalog)

    def classify_job_skills(self, job_description: str) -> dict[str, list[str]]:
        text = str(job_description or "")
        all_skills = set(self.extract_job_skills(text))
        required: set[str] = set()
        preferred: set[str] = set()
        sections = re.split(r"[\n\r]+|(?<=[.!?])\s+", text)
        parser = ResumeParser()
        for section in sections:
            lowered = section.lower()
            skills = set(parser.extract_skills(section, self.skill_catalog))
            if not skills:
                continue
            if any(marker in lowered for marker in self.PREFERRED_MARKERS):
                preferred.update(skills)
            elif any(marker in lowered for marker in self.REQUIRED_MARKERS):
                required.update(skills)
        preferred -= required
        general = all_skills - required - preferred
        return {"required": sorted(required), "preferred": sorted(preferred), "general": sorted(general)}

    def match(self, resume_skills: Iterable[str], job_skills: Iterable[str] | None = None, job_description: str | None = None) -> dict:
        resume = self._normalize_skills(resume_skills)
        if job_skills is not None:
            job = self._normalize_skills(job_skills)
            required, preferred, general = set(), set(), job
        else:
            groups = self.classify_job_skills(job_description or "")
            required, preferred, general = set(groups["required"]), set(groups["preferred"]), set(groups["general"])
            job = required | preferred | general
        matched = sorted(resume & job)
        missing = sorted(job - resume)
        extra = sorted(resume - job)
        return {
            "score": self._weighted_score(resume, required, preferred, general),
            "matched_skills": matched,
            "missing_skills": missing,
            "resume_only_skills": extra,
            "required_skills": sorted(required),
            "preferred_skills": sorted(preferred),
            "general_skills": sorted(general),
            "missing_required_skills": sorted(required - resume),
            "matched_required_skills": sorted(required & resume),
            "resume_skill_count": len(resume),
            "job_skill_count": len(job),
            "matched_skill_count": len(matched),
        }

    @staticmethod
    def _weighted_score(resume, required, preferred, general) -> float:
        if not (required or preferred or general):
            return 0.0
        if not required and not preferred:
            return round(len(resume & general) / len(general) * 100, 2)
        weights = {"required": 3.0, "general": 2.0, "preferred": 1.0}
        total = len(required) * 3.0 + len(general) * 2.0 + len(preferred)
        earned = len(resume & required) * 3.0 + len(resume & general) * 2.0 + len(resume & preferred)
        return round(earned / total * 100, 2) if total else 0.0

    def match_job(self, resume_skills: Iterable[str], job) -> dict:
        """Match against title plus description so title-only listings are not forced to score zero."""
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
        combined = " ".join(part for part in (str(title or "").strip(), str(description or "").strip()) if part)
        result = self.match(resume_skills, job_description=combined)
        result.update({"title": title, "company": company, "apply_url": apply_url})
        return result

    def rank_jobs(self, resume_skills: Iterable[str], jobs: Iterable) -> list[dict]:
        results = [self.match_job(resume_skills, job) for job in jobs]
        return sorted(results, key=lambda item: (-item["score"], str(item.get("company", "")).lower(), str(item.get("title", "")).lower()))

    @staticmethod
    def _normalize_skills(skills: Iterable[str] | None) -> set[str]:
        if not skills:
            return set()
        normalized = set()
        for skill in skills:
            value = re.sub(r"\s+", " ", str(skill or "").strip().lower())
            if value:
                normalized.add(value)
        return normalized
