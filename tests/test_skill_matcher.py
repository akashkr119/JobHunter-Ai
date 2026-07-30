"""Unit tests for skill matcher."""

from matcher.skill_matcher import SkillMatcher


def test_skill_matcher_instance():
    matcher = SkillMatcher()
    assert matcher is not None


def test_has_match_method():
    matcher = SkillMatcher()
    assert hasattr(matcher, 'match')


def test_match_method_is_callable():
    matcher = SkillMatcher()
    assert callable(matcher.match)
