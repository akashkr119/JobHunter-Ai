"""Utilities for locating career pages on company websites."""

from urllib.parse import urljoin, urlparse


class CareerFinder:
    """Generate likely career-page URLs for a company website."""

    COMMON_PATHS = (
        "careers",
        "jobs",
        "careers/jobs",
        "career",
        "join-us",
        "joinus",
        "work-with-us",
        "work-withus",
        "opportunities",
        "careers/search",
        "jobs/search",
    )

    def candidate_urls(self, website_url: str) -> list[str]:
        """Return common career-page candidates for a company website."""
        base = self._normalize_website(website_url)
        return [urljoin(f"{base}/", path) for path in self.COMMON_PATHS]

    def find(self, website_url: str) -> list[str]:
        """Return career-page candidates for the discovery pipeline.

        Network probing is intentionally kept outside this method so unit tests
        and local development remain deterministic. A later crawler stage can
        request these candidates and select the first valid careers page.
        """
        return self.candidate_urls(website_url)

    @staticmethod
    def _normalize_website(website_url: str) -> str:
        """Validate and normalize a company website URL."""
        if website_url is None:
            raise ValueError("Website URL cannot be empty")

        url = str(website_url).strip()
        if not url:
            raise ValueError("Website URL cannot be empty")

        if not urlparse(url).scheme:
            url = f"https://{url}"

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid website URL: {website_url}")

        return url.rstrip("/")
