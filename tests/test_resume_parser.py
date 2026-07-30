"""Unit tests for resume parser."""

from matcher.resume_parser import ResumeParser


def test_resume_parser_instance():
    parser = ResumeParser()
    assert parser is not None


def test_has_parse_method():
    parser = ResumeParser()
    assert hasattr(parser, 'parse')


def test_parse_method_is_callable():
    parser = ResumeParser()
    assert callable(parser.parse)
