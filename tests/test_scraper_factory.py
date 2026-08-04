"""Unit tests for ATS scraper factory."""

import pytest

from crawler.greenhouse_scraper import GreenhouseScraper
from crawler.lever_scraper import LeverScraper
from crawler.scraper_factory import ScraperFactory
from crawler.smartrecruiters_scraper import SmartRecruitersScraper
from crawler.workday_scraper import WorkdayScraper


@pytest.mark.parametrize(
    ("platform", "expected_type"),
    [
        ("greenhouse", GreenhouseScraper),
        ("lever", LeverScraper),
        ("workday", WorkdayScraper),
        ("smartrecruiters", SmartRecruitersScraper),
    ],
)
def test_create_supported_scraper(platform, expected_type):
    factory = ScraperFactory()
    assert isinstance(factory.create(platform), expected_type)


@pytest.mark.parametrize(
    ("url", "expected_type"),
    [
        ("https://boards.greenhouse.io/example", GreenhouseScraper),
        ("https://jobs.lever.co/example", LeverScraper),
        ("https://example.wd5.myworkdayjobs.com/en-US/Careers", WorkdayScraper),
        ("https://jobs.smartrecruiters.com/Example", SmartRecruitersScraper),
    ],
)
def test_from_url_routes_to_correct_scraper(url, expected_type):
    factory = ScraperFactory()
    assert isinstance(factory.from_url(url), expected_type)


def test_platform_name_is_case_insensitive():
    factory = ScraperFactory()
    assert isinstance(factory.create("GreenHouse"), GreenhouseScraper)


def test_unsupported_platform_rejected():
    factory = ScraperFactory()
    with pytest.raises(ValueError, match="Unsupported ATS platform"):
        factory.create("oracle")


def test_unknown_url_rejected():
    factory = ScraperFactory()
    with pytest.raises(ValueError, match="Unable to detect supported ATS"):
        factory.from_url("https://example.com/careers")


def test_page_content_can_drive_routing():
    factory = ScraperFactory()
    html = '<a href="https://jobs.lever.co/example">Jobs</a>'
    assert isinstance(
        factory.from_url("https://example.com/careers", page_content=html),
        LeverScraper,
    )
