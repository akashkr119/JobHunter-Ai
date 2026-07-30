"""Utilities for matching resume skills against job requirements."""


class SkillMatcher:
    """Compute a simple overlap score between resume and job skills."""

    def match(self, resume_skills: list[str], job_skills: list[str]) -> dict:
        resume = {s.strip().lower() for s in resume_skills if s.strip()}
        job = {s.strip().lower() for s in job_skills if s.strip()}

        matched = sorted(resume & job)
        score = round((len(matched) / len(job)) * 100, 2) if job else 0.0

        return {
            "score": score,
            "matched_skills": matched,
            "missing_skills": sorted(job - resume),
        }
