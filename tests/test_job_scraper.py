"""Unit tests for job scraper."""

from crawler.job_scraper import JobScraper


def test_job_scraper_instance():
    scraper = JobScraper()
    assert scraper is not None


def test_has_scrape_method():
    scraper = JobScraper()
    assert hasattr(scraper, 'scrape')


def test_scrape_method_is_callable():
    scraper = JobScraper()
    assert callable(scraper.scrape)
