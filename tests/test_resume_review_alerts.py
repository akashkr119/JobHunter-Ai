from matcher.resume_improvement import ResumeImprovement
from notifier.notifier import Notifier


def test_resume_review_alert_includes_required_review_details():
    recommendations = (
        ResumeImprovement("Selenium", "Review truthful Selenium evidence."),
        ResumeImprovement("pytest", "Review truthful pytest evidence."),
    )
    alert = Notifier.format_resume_review_alert(
        {"title": "Senior QA Engineer", "company": "Example Corp", "source": "Adzuna"},
        67,
        recommendations,
        application_status="paused",
    )

    assert "Resume Modification Required" in alert
    assert "Job: Senior QA Engineer — Example Corp" in alert
    assert "Match: 67%" in alert
    assert "Source: Adzuna" in alert
    assert "• Selenium: Review truthful Selenium evidence." in alert
    assert "• pytest: Review truthful pytest evidence." in alert
    assert "Application status: PAUSED" in alert
    assert "Review and update the resume before applying" in alert


def test_resume_review_alert_requires_recommendations():
    try:
        Notifier.format_resume_review_alert(
            {"title": "QA Engineer", "company": "Example Corp"},
            61,
            (),
        )
    except ValueError as exc:
        assert str(exc) == "At least one resume recommendation is required"
    else:
        raise AssertionError("Expected ValueError")


def test_resume_review_alert_does_not_submit_application():
    recommendations = (ResumeImprovement("Python", "Review truthful Python evidence."),)
    alert = Notifier.format_resume_review_alert(
        {"title": "QA Engineer", "company": "Example Corp"},
        64,
        recommendations,
    )
    assert "submit" not in alert.lower()
