"""Utilities for locating career pages on company websites."""

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import REQUEST_TIMEOUT, USER_AGENT


class CareerFinder:
    """Discover career pages and provide deterministic fallback candidates."""

    COMMON_PATHS = (
        "careers", "jobs", "careers/jobs", "career", "join-us", "joinus",
        "work-with-us", "work-withus", "opportunities", "careers/search", "jobs/search",
    )
    CAREER_KEYWORDS = (
        "career", "careers", "job", "jobs", "join us", "join-us", "joinus",
        "work with us", "work-with-us", "opportunities", "open positions",
        "open roles", "vacancies",
    )

    def __init__(self, session=None, timeout: int = REQUEST_TIMEOUT):
        self.session = session or requests.Session()
        self.timeout = timeout

    def candidate_urls(self, website_url: str) -> list[str]:
        """Return common career-page candidates for a company website."""
        base = self._normalize_website(website_url)
        return [urljoin(f"{base}/", path) for path in self.COMMON_PATHS]

    def discover(self, website_url: str) -> list[str]:
        """Discover career-related links directly from a company homepage."""
        base = self._normalize_website(website_url)
        response = self.session.get(
            base,
            timeout=self.timeout,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        discovered = []
        seen = set()

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            text = " ".join(anchor.stripped_strings).lower()
            absolute = urljoin(f"{base}/", href)
            parsed = urlparse(absolute)
            haystack = f"{text} {parsed.path.lower()} {parsed.netloc.lower()}"
            if not any(keyword in haystack for keyword in self.CAREER_KEYWORDS):
                continue
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            normalized = absolute.rstrip("/")
            if normalized not in seen:
                seen.add(normalized)
                discovered.append(normalized)

        return discovered

    def find(self, website_url: str, discover: bool = False) -> list[str]:
        """Return discovered career links followed by common fallback URLs.

        ``discover=False`` preserves the original deterministic behavior for
        callers/tests. Set it to True when network discovery is desired.
        """
        candidates = self.candidate_urls(website_url)
        if not discover:
            return candidates
        try:
            discovered = self.discover(website_url)
        except requests.RequestException:
            discovered = []
        return list(dict.fromkeys([*discovered, *candidates]))

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
