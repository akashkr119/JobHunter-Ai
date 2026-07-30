"""Utilities for locating career pages on company websites."""

from urllib.parse import urljoin


class CareerFinder:
    """Generate common career page URLs for a company website."""

    COMMON_PATHS = (
        "careers",
        "jobs",
        "careers/jobs",
        "join-us",
        "work-with-us",
    )

    def candidate_urls(self, website_url: str) -> list[str]:
        base = website_url.rstrip("/") + "/"
        return [urljoin(base, path) for path in self.COMMON_PATHS]
