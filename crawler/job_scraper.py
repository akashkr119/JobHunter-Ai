"""Base job scraper interfaces and data models."""

from dataclasses import dataclass


@dataclass
class Job:
    title: str
    company: str
    location: str
    apply_url: str


class JobScraper:
    """Base class for all ATS-specific job scrapers."""

    def scrape(self, career_url: str) -> list[Job]:
        """Return job listings from the supplied career page."""
        raise NotImplementedError("Implement scraper for the target ATS platform.")
