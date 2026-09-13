"""Decide whether a resume gap needs review before application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from matcher.resume_gap import ResumeGapAnalysis
from matcher.resume_improvement import ResumeImprovement, recommend_resume_improvements


@dataclass(frozen=True)
class ResumeReviewDecision:
    """Review decision derived without changing the user's resume."""

    recommendations: tuple[ResumeImprovement, ...]
    requires_modification: bool


def evaluate_resume_review(
    analysis: ResumeGapAnalysis,
    *,
    confirmed_skills: Iterable[str] = (),
) -> ResumeReviewDecision:
    """Determine whether truthful resume evidence should be reviewed.

    Missing skills are never treated as resume evidence. A modification is
    considered required only when the user has explicitly confirmed a skill
    and the current resume may need truthful evidence for it.
    """
    confirmed = {skill.strip().lower() for skill in confirmed_skills if skill.strip()}
    recommendations = recommend_resume_improvements(
        analysis, confirmed_skills=confirmed
    )
    requires_modification = any(
        recommendation.skill.strip().lower() in confirmed
        for recommendation in recommendations
    )
    return ResumeReviewDecision(
        recommendations=recommendations,
        requires_modification=requires_modification,
    )
