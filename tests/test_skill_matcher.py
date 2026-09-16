"""Regression tests for conservative resume/job skill matching."""

from crawler.job_scraper import Job
from matcher.resume_parser import ResumeParser
from matcher.skill_matcher import SkillMatcher


def test_skill_matcher_instance():
    assert SkillMatcher() is not None


def test_match_calculates_score_and_missing_skills():
    result = SkillMatcher().match(["Python", "Selenium", "Pytest"], ["python", "selenium", "docker", "pytest"])
    assert result["score"] == 75.0
    assert result["matched_skills"] == ["pytest", "python", "selenium"]
    assert result["missing_skills"] == ["docker"]
    assert result["matched_skill_count"] == 3


def test_match_is_case_insensitive_and_removes_duplicates():
    result = SkillMatcher().match(["Python", " python ", "SELENIUM"], ["PYTHON", "selenium"])
    assert result["score"] == 100.0
    assert result["matched_skills"] == ["python", "selenium"]
    assert result["is_relevant"] is True


def test_extract_job_skills_from_description():
    skills = SkillMatcher().extract_job_skills("We need Python, Selenium, Pytest and Jenkins experience.")
    assert {"python", "selenium", "pytest", "jenkins"}.issubset(skills)


def test_can_is_not_extracted_from_normal_english():
    skills = ResumeParser().extract_skills("You can work with customers and can communicate clearly.")
    assert "can" not in skills
    assert "can bus" not in skills


def test_can_bus_requires_explicit_protocol_context():
    skills = ResumeParser().extract_skills("Experience with CAN bus, UDS and CAN communication.")
    assert "can bus" in skills
    assert "uds" in skills


def test_skill_aliases_are_canonicalized():
    skills = ResumeParser().extract_skills("Selenium WebDriver, RESTful APIs, automated testing and embedded systems")
    assert "selenium" in skills
    assert "rest api" in skills
    assert "automation testing" in skills
    assert "embedded systems" in skills


def test_missing_required_skill_hurts_more_than_missing_preferred_skill():
    matcher = SkillMatcher()
    description = "Requirements: Python and Selenium are required.\nNice to have: Docker."
    missing_preferred = matcher.match(["python", "selenium"], job_description=description)
    missing_required = matcher.match(["python", "docker"], job_description=description)
    assert missing_preferred["score"] > missing_required["score"]
    assert missing_preferred["missing_required_skills"] == []
    assert "selenium" in missing_required["missing_required_skills"]
    assert missing_required["score"] < 60


def test_single_incidental_skill_is_not_a_relevant_match():
    result = SkillMatcher().match(["python", "selenium", "pytest"], ["python", "java", "aws", "kubernetes"])
    assert result["matched_skills"] == ["python"]
    assert result["is_relevant"] is False
    assert result["match_confidence"] == "low"


def test_required_single_skill_can_establish_relevance():
    result = SkillMatcher().match(["python"], job_description="Required: Python. Nice to have: AWS.")
    assert result["score"] == 75.0
    assert result["is_relevant"] is True


def test_match_job_uses_job_description():
    matcher = SkillMatcher()
    job = Job(title="QA Automation Engineer", company="Example", location="Bengaluru", apply_url="https://example.com/jobs/1", description="Python Selenium Pytest Docker", platform="greenhouse")
    result = matcher.match_job(["python", "selenium", "pytest"], job)
    assert result["score"] == 75.0
    assert result["title"] == "QA Automation Engineer"
    assert result["missing_skills"] == ["docker"]
    assert result["is_relevant"] is True


def test_match_job_uses_title_when_description_is_empty():
    matcher = SkillMatcher()
    job = Job(title="Python Selenium Automation Engineer", company="Example", location="Bengaluru", apply_url="https://example.com/jobs/2", description="", platform="generic")
    result = matcher.match_job(["python", "selenium"], job)
    assert result["score"] == 100.0
    assert result["is_relevant"] is True


def test_empty_job_skills_returns_zero_score_and_is_not_relevant():
    result = SkillMatcher().match(["python"], [])
    assert result["score"] == 0.0
    assert result["is_relevant"] is False
