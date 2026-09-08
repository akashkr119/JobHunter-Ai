from matcher.resume_gap import ResumeGapAnalysis
from matcher.resume_improvement import recommend_resume_improvements


def test_missing_skill_gets_conservative_learning_guidance():
    analysis = ResumeGapAnalysis(
        resume_skills=("python",),
        job_skills=("python", "docker"),
        missing_skills=("docker",),
        matched_skills=("python",),
    )

    result = recommend_resume_improvements(analysis)

    assert len(result) == 1
    assert result[0].skill == "docker"
    assert "do not add" in result[0].action.lower()


def test_confirmed_skill_gets_evidence_review_guidance():
    analysis = ResumeGapAnalysis(
        resume_skills=(),
        job_skills=("selenium",),
        missing_skills=("selenium",),
        matched_skills=(),
    )

    result = recommend_resume_improvements(analysis, confirmed_skills=("Selenium",))

    assert result[0].skill == "selenium"
    assert "truthful evidence" in result[0].action.lower()


def test_no_gaps_produces_no_recommendations():
    analysis = ResumeGapAnalysis(
        resume_skills=("python",),
        job_skills=("python",),
        missing_skills=(),
        matched_skills=("python",),
    )

    assert recommend_resume_improvements(analysis) == ()
