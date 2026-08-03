"""Base job scraper interfaces and data models."""

from dataclasses import asdict, dataclass
from urllib.parse import urljoin, urlparse


@dataclass
class Job:
    """Normalized job listing used throughout the application."""

    title: str
    company: str
    location: str
    apply_url: str
    description: str = ""
    platform: str = "unknown"

    def to_dict(self) -> dict:
        """Return a serializable representation of the job."""
        return asdict(self)


class JobScraper:
    """Base class for generic and ATS-specific job scrapers."""

    def scrape(self, career_url: str) -> list[Job]:
        """Return job listings from the supplied career page.

        ATS-specific subclasses should override this method. Keeping the base
        implementation explicit prevents silent empty results in production.
        """
        self.validate_url(career_url)
        raise NotImplementedError("Implement scraper for the target ATS platform.")

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate a career-page URL and return its normalized form."""
        if url is None:
            raise ValueError("Career page URL cannot be empty")

        candidate = str(url).strip()
        if not candidate:
            raise ValueError("Career page URL cannot be empty")

        if not urlparse(candidate).scheme:
            candidate = f"https://{candidate}"

        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid career page URL: {url}")

        return candidate

    @staticmethod
    def make_job(
        *,
        title: str,
        company: str,
        location: str = "",
        apply_url: str,
        base_url: str | None = None,
        description: str = "",
        platform: str = "unknown",
    ) -> Job:
        """Create a normalized :class:`Job` from scraper output."""
        title = str(title or "").strip()
        company = str(company or "").strip()
        location = str(location or "").strip()
        description = str(description or "").strip()
        platform = str(platform or "unknown").strip().lower()

        if not title:
            raise ValueError("Job title cannot be empty")
        if not company:
            raise ValueError("Company name cannot be empty")
        if not apply_url:
            raise ValueError("Apply URL cannot be empty")

        normalized_apply_url = str(apply_url).strip()
        if base_url:
            normalized_apply_url = urljoin(base_url, normalized_apply_url)

        normalized_apply_url = JobScraper.validate_url(normalized_apply_url)

        return Job(
            title=title,
            company=company,
            location=location,
            apply_url=normalized_apply_url,
            description=description,
            platform=platform,
        )
