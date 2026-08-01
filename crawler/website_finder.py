"""Utilities for finding and normalizing company websites."""

from urllib.parse import quote_plus, urlparse


class WebsiteFinder:
    """Build search queries and normalize known company website URLs."""

    SEARCH_ENGINE = "https://www.google.com/search?q="

    def build_search_url(self, company_name: str) -> str:
        """Build a search URL for locating a company's official website."""
        company_name = self._clean_company_name(company_name)
        query = quote_plus(f"{company_name} official website")
        return f"{self.SEARCH_ENGINE}{query}"

    def find(self, company_name: str, website: str | None = None) -> str:
        """Return a normalized known website or a discovery search URL.

        The project currently does not depend on a paid search API. If a
        website is already supplied from the input data, it is normalized and
        returned directly. Otherwise a search URL is returned for the discovery
        stage of the pipeline.
        """
        company_name = self._clean_company_name(company_name)

        if website and str(website).strip():
            return self.normalize_url(str(website))

        return self.build_search_url(company_name)

    def normalize_url(self, url: str) -> str:
        """Normalize a website URL and ensure it has an HTTP scheme."""
        url = url.strip()
        if not url:
            raise ValueError("Website URL cannot be empty")

        if not urlparse(url).scheme:
            url = f"https://{url}"

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid website URL: {url}")

        return url.rstrip("/")

    @staticmethod
    def _clean_company_name(company_name: str) -> str:
        """Validate and clean a company name."""
        if company_name is None:
            raise ValueError("Company name cannot be empty")

        cleaned = str(company_name).strip()
        if not cleaned:
            raise ValueError("Company name cannot be empty")

        return cleaned
