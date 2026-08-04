"""Unit tests for resume parser."""

import pytest

from matcher.resume_parser import ResumeParser


def test_resume_parser_instance():
    parser = ResumeParser()
    assert parser is not None


def test_has_parse_method():
    parser = ResumeParser()
    assert hasattr(parser, "parse")


def test_parse_method_is_callable():
    parser = ResumeParser()
    assert callable(parser.parse)


def test_extract_text_reads_plain_text_resume(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python Selenium Pytest", encoding="utf-8")

    parser = ResumeParser()
    assert parser.extract_text(resume) == "Python Selenium Pytest"


def test_extract_skills_is_case_insensitive():
    parser = ResumeParser()
    skills = parser.extract_skills("PYTHON, Selenium, pytest and Docker")

    assert "python" in skills
    assert "selenium" in skills
    assert "pytest" in skills
    assert "docker" in skills


def test_extract_skills_detects_automotive_skills():
    parser = ResumeParser()
    skills = parser.extract_skills(
        "Automotive testing experience with CAN, CANoe, CAPL and UDS."
    )

    assert "automotive" in skills
    assert "can" in skills
    assert "canoe" in skills
    assert "capl" in skills
    assert "uds" in skills


def test_parse_returns_structured_resume(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text(
        "QA Automation Engineer with Python, Selenium, Pytest and Jenkins.",
        encoding="utf-8",
    )

    parser = ResumeParser()
    result = parser.parse(resume)

    assert result["path"] == str(resume)
    assert "QA Automation Engineer" in result["text"]
    assert "python" in result["skills"]
    assert "selenium" in result["skills"]
    assert "pytest" in result["skills"]
    assert "jenkins" in result["skills"]


def test_missing_resume_raises_file_not_found(tmp_path):
    parser = ResumeParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(tmp_path / "missing.txt")


def test_unsupported_resume_format_rejected(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"not a real pdf")

    parser = ResumeParser()
    with pytest.raises(ValueError, match="Unsupported resume format"):
        parser.parse(resume)


def test_markdown_resume_is_supported(tmp_path):
    resume = tmp_path / "resume.md"
    resume.write_text("# Skills\nPython\nSelenium", encoding="utf-8")

    result = ResumeParser().parse(resume)
    assert "python" in result["skills"]
    assert "selenium" in result["skills"]
