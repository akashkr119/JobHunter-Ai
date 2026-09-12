from matcher.resume_gap import ResumeGapAnalysis
from matcher.resume_review import evaluate_resume_review


def test_resume_review_requires_modification_for_confirmed_gap():
    analysis = ResumeGapAnalysis(
        resume_skills=("python",),
        job_skills=("python", "selenium"),
        missing_skills=("selenium",),
        matched_skills=("python",),
    )

    decision = evaluate_resume_review(analysis, confirmed_skills=("selenium",))

    assert decision.requires_modification is True
    assert decision.recommendations[0].skill == "selenium"


def test_unconfirmed_gap_does_not_require_resume_modification():
    analysis = ResumeGapAnalysis(
        resume_skills=("python",),
        job_skills=("python", "selenium"),
        missing_skills=("selenium",),
        matched_skills=("python",),
    )

    decision = evaluate_resume_review(analysis)

    assert decision.requires_modification is False
    assert len(decision.recommendations) == 1
