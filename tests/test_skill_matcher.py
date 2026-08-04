"""Unit tests for skill matcher."""

from crawler.job_scraper import Job
from matcher.skill_matcher import SkillMatcher


def test_skill_matcher_instance():
    matcher = SkillMatcher()
    assert matcher is not None


def test_has_match_method():
    matcher = SkillMatcher()
    assert hasattr(matcher, "match")


def test_match_method_is_callable():
    matcher = SkillMatcher()
    assert callable(matcher.match)


def test_match_calculates_score_and_missing_skills():
    matcher = SkillMatcher()
    result = matcher.match(
        ["Python", "Selenium", "Pytest"],
        ["python", "selenium", "docker", "pytest"],
    )

    assert result["score"] == 75.0
    assert result["matched_skills"] == ["pytest", "python", "selenium"]
    assert result["missing_skills"] == ["docker"]
    assert result["matched_skill_count"] == 3
    assert result["job_skill_count"] == 4


def test_match_is_case_insensitive_and_removes_duplicates():
    matcher = SkillMatcher()
    result = matcher.match(
        ["Python", " python ", "SELENIUM"],
        ["PYTHON", "selenium"],
    )

    assert result["score"] == 100.0
    assert result["matched_skills"] == ["python", "selenium"]


def test_extract_job_skills_from_description():
    matcher = SkillMatcher()
    skills = matcher.extract_job_skills(
        "We need Python, Selenium, Pytest and Jenkins experience."
    )

    assert "python" in skills
    assert "selenium" in skills
    assert "pytest" in skills
    assert "jenkins" in skills


def test_match_job_uses_job_description():
    matcher = SkillMatcher()
    job = Job(
        title="QA Automation Engineer",
        company="Example",
        location="Bengaluru",
        apply_url="https://example.com/jobs/1",
        description="Python Selenium Pytest Docker",
        platform="greenhouse",
    )

    result = matcher.match_job(["python", "selenium", "pytest"], job)

    assert result["score"] == 75.0
    assert result["title"] == "QA Automation Engineer"
    assert result["company"] == "Example"
    assert result["missing_skills"] == ["docker"]


def test_rank_jobs_best_match_first():
    matcher = SkillMatcher()
    jobs = [
        Job(
            title="DevOps Engineer",
            company="Company B",
            location="Remote",
            apply_url="https://example.com/jobs/2",
            description="Python Docker Kubernetes AWS",
        ),
        Job(
            title="QA Automation Engineer",
            company="Company A",
            location="Bengaluru",
            apply_url="https://example.com/jobs/1",
            description="Python Selenium Pytest",
        ),
    ]

    ranked = matcher.rank_jobs(["python", "selenium", "pytest"], jobs)

    assert ranked[0]["title"] == "QA Automation Engineer"
    assert ranked[0]["score"] == 100.0
    assert ranked[1]["score"] == 25.0


def test_empty_job_skills_returns_zero_score():
    matcher = SkillMatcher()
    result = matcher.match(["python"], [])
    assert result["score"] == 0.0
