"""Lever ATS job-postings scraper."""

import html
import re
from urllib.parse import urlparse

import requests

from crawler.job_scraper import Job, JobScraper


class LeverScraper(JobScraper):
    """Fetch public job listings from Lever's postings API."""

    API_TEMPLATE = "https://api.lever.co/v0/postings/{site}?mode=json"

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def scrape(self, career_url: str, company: str = "") -> list[Job]:
        """Fetch and normalize jobs from a Lever careers URL."""
        career_url = self.validate_url(career_url)
        site = self.extract_site(career_url)
        api_url = self.API_TEMPLATE.format(site=site)

        response = requests.get(
            api_url,
            timeout=self.timeout,
            headers={"User-Agent": "JobHunter-Ai/1.0"},
        )
        response.raise_for_status()
        postings = response.json()

        if not isinstance(postings, list):
            return []

        jobs: list[Job] = []
        for item in postings:
            title = item.get("text", "")
            categories = item.get("categories") or {}
            location = categories.get("location", "")
            apply_url = item.get("hostedUrl") or item.get("applyUrl", "")
            description = self._description(item)
            job_company = company.strip() or site

            if not title or not apply_url:
                continue

            jobs.append(
                self.make_job(
                    title=title,
                    company=job_company,
                    location=location,
                    apply_url=apply_url,
                    description=description,
                    platform="lever",
                )
            )

        return jobs

    @staticmethod
    def extract_site(career_url: str) -> str:
        """Extract the Lever company/site token from a public careers URL."""
        candidate = career_url.strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        parts = [part for part in parsed.path.split("/") if part]

        if not (host.endswith("lever.co") or host.endswith("lever.co")):
            raise ValueError(f"Not a Lever career URL: {career_url}")
        if not parts:
            raise ValueError(f"Lever site token not found in URL: {career_url}")

        if host == "api.lever.co" and len(parts) >= 3 and parts[0] == "v0" and parts[1] == "postings":
            return parts[2]

        return parts[0]

    @staticmethod
    def _description(item: dict) -> str:
        """Build compact plain-text description from Lever posting fields."""
        pieces = [
            item.get("descriptionPlain", ""),
            item.get("description", ""),
            item.get("additionalPlain", ""),
            item.get("additional", ""),
        ]
        text = " ".join(str(piece) for piece in pieces if piece)
        text = html.unescape(text)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()
