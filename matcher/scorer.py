"""Utilities for calculating an overall job match score."""


class JobScorer:
    """Combine weighted factors into a single score."""

    DEFAULT_WEIGHTS = {
        "skill": 0.7,
        "experience": 0.2,
        "location": 0.1,
    }

    def score(self, skill_score: float, experience_score: float = 100.0, location_score: float = 100.0) -> float:
        weights = self.DEFAULT_WEIGHTS
        total = (
            skill_score * weights["skill"]
            + experience_score * weights["experience"]
            + location_score * weights["location"]
        )
        return round(total, 2)
