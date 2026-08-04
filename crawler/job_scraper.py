"""Base job scraper interfaces and data models."""

import html
import re
from dataclasses import asdict, dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


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
        """Return job listings from the supplied career page."""
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
    def clean_description(value: str) -> str:
        """Convert ATS HTML/text into stable plain text for skill matching.

        Script/style content is discarded, common block elements retain word
        boundaries, HTML entities are decoded, and repeated whitespace is
        collapsed. This prevents skill matching from being distorted by markup.
        """
        raw = html.unescape(str(value or ""))
        if not raw.strip():
            return ""
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def combine_description(*values) -> str:
        """Combine multiple ATS description fields without duplicate text."""
        pieces = []
        seen = set()
        for value in values:
            cleaned = JobScraper.clean_description(value)
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                pieces.append(cleaned)
        return " ".join(pieces)

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
        title = re.sub(r"\s+", " ", str(title or "")).strip()
        company = re.sub(r"\s+", " ", str(company or "")).strip()
        location = re.sub(r"\s+", " ", str(location or "")).strip()
        description = JobScraper.clean_description(description)
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
