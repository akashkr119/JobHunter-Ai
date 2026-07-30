"""Unit tests for website finder."""

from crawler.website_finder import WebsiteFinder


def test_website_finder_instance():
    finder = WebsiteFinder()
    assert finder is not None


def test_has_find_method():
    finder = WebsiteFinder()
    assert hasattr(finder, "find")


def test_find_is_callable():
    finder = WebsiteFinder()
    assert callable(finder.find)
