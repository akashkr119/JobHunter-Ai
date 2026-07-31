"""Utilities for locating career pages on company websites."""

from urllib.parse import urljoin

class CareerFinder:
    """Generate common career page URLs for a company website."""
    COMMON_PATHS=("careers","jobs","careers/jobs","join-us","work-with-us")
    def candidate_urls(self, website_url:str)->list[str]:
        base=website_url.rstrip("/")+"/"
        return [urljoin(base,p) for p in self.COMMON_PATHS]
    def find(self, website_url:str)->list[str]:
        return self.candidate_urls(website_url)
