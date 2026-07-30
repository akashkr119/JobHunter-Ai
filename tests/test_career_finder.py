"""Unit tests for career finder."""

from crawler.career_finder import CareerFinder


def test_career_finder_instance():
    finder = CareerFinder()
    assert finder is not None


def test_has_find_method():
    finder = CareerFinder()
    assert hasattr(finder, 'find')


def test_find_method_is_callable():
    finder = CareerFinder()
    assert callable(finder.find)
