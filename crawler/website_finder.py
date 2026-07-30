"""Find the official website for a company."""

from urllib.parse import quote_plus


class WebsiteFinder:
    """Builds a search query for locating a company's official website."""

    SEARCH_ENGINE = "https://www.google.com/search?q="

    def build_search_url(self, company_name: str) -> str:
        query = quote_plus(f"{company_name} official website")
        return f"{self.SEARCH_ENGINE}{query}"
