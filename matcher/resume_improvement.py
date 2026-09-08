"""Conservative resume improvement recommendations from detected job gaps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from matcher.resume_gap import ResumeGapAnalysis


@dataclass(frozen=True)
class ResumeImprovement:
    """A reviewable improvement suggestion for a detected skill gap."""

    skill: str
    action: str


def recommend_resume_improvements(
    analysis: ResumeGapAnalysis,
    *,
    confirmed_skills: Iterable[str] = (),
) -> tuple[ResumeImprovement, ...]:
    """Suggest safe resume-review actions without inventing experience.

    A missing skill is never added to the resume automatically. Only skills
    explicitly supplied in ``confirmed_skills`` are eligible for an
    evidence-focused resume suggestion.
    """
    confirmed = {skill.strip().lower() for skill in confirmed_skills if skill.strip()}
    recommendations: list[ResumeImprovement] = []

    for skill in analysis.missing_skills:
        normalized = skill.strip().lower()
        if normalized in confirmed:
            action = (
                "Review the resume for truthful evidence of this skill and "
                "add the evidence if it is currently missing."
            )
        else:
            action = (
                "Gap detected; do not add this skill unless you genuinely have "
                "the experience. Consider learning it or documenting real evidence."
            )
        recommendations.append(ResumeImprovement(skill=skill, action=action))

    return tuple(recommendations)
