"""Unit tests for skill matcher."""

from crawler.job_scraper import Job
from matcher.skill_matcher import SkillMatcher


def test_skill_matcher_instance():
    assert SkillMatcher() is not None


def test_has_match_method():
    assert hasattr(SkillMatcher(), "match")


def test_match_method_is_callable():
    assert callable(SkillMatcher().match)


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
    result = SkillMatcher().match(
        ["Python", " python ", "SELENIUM"], ["PYTHON", "selenium"]
    )
    assert result["score"] == 100.0
    assert result["matched_skills"] == ["python", "selenium"]


def test_extract_job_skills_from_description():
    skills = SkillMatcher().extract_job_skills(
        "We need Python, Selenium, Pytest and Jenkins experience."
    )
    assert {"python", "selenium", "pytest", "jenkins"}.issubset(skills)


def test_classify_required_and_preferred_skills():
    matcher = SkillMatcher()
    groups = matcher.classify_job_skills(
        "Requirements: Python and Selenium are required.\n"
        "Nice to have: Docker and AWS.\n"
        "You will also use Jenkins."
    )
    assert {"python", "selenium"}.issubset(groups["required"])
    assert {"docker", "aws"}.issubset(groups["preferred"])
    assert "jenkins" in groups["general"]


def test_missing_required_skill_hurts_more_than_missing_preferred_skill():
    matcher = SkillMatcher()
    description = (
        "Requirements: Python and Selenium are required.\n"
        "Nice to have: Docker."
    )
    missing_preferred = matcher.match(
        ["python", "selenium"], job_description=description
    )
    missing_required = matcher.match(
        ["python", "docker"], job_description=description
    )
    assert missing_preferred["score"] > missing_required["score"]
    assert missing_preferred["missing_required_skills"] == []
    assert "selenium" in missing_required["missing_required_skills"]


def test_required_skill_receives_more_weight_than_preferred_skill():
    matcher = SkillMatcher()
    description = "Required: Python. Nice to have: Docker."
    required_match = matcher.match(["python"], job_description=description)
    preferred_match = matcher.match(["docker"], job_description=description)
    assert required_match["score"] > preferred_match["score"]


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


def test_match_job_uses_title_when_description_is_empty():
    matcher = SkillMatcher()
    job = Job(
        title="Python Selenium Automation Engineer",
        company="Example",
        location="Bengaluru",
        apply_url="https://example.com/jobs/2",
        description="",
        platform="generic",
    )
    result = matcher.match_job(["python", "selenium"], job)
    assert result["score"] == 100.0
    assert result["matched_skills"] == ["python", "selenium"]


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
    assert SkillMatcher().match(["python"], [])["score"] == 0.0
