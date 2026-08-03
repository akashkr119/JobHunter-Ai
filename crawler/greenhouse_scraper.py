"""Greenhouse ATS job-board scraper."""

import html
import re
from urllib.parse import urlparse

import requests

from crawler.job_scraper import Job, JobScraper


class GreenhouseScraper(JobScraper):
    """Fetch public job listings from Greenhouse's job-board API."""

    API_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def scrape(self, career_url: str, company: str = "") -> list[Job]:
        """Fetch and normalize jobs from a Greenhouse board URL."""
        career_url = self.validate_url(career_url)
        board_token = self.extract_board_token(career_url)
        api_url = self.API_TEMPLATE.format(board_token=board_token)

        response = requests.get(
            api_url,
            params={"content": "true"},
            timeout=self.timeout,
            headers={"User-Agent": "JobHunter-Ai/1.0"},
        )
        response.raise_for_status()
        payload = response.json()

        jobs: list[Job] = []
        for item in payload.get("jobs", []):
            title = item.get("title", "")
            location = (item.get("location") or {}).get("name", "")
            apply_url = item.get("absolute_url", "")
            description = self._plain_text(item.get("content", ""))
            job_company = company.strip() or board_token

            if not title or not apply_url:
                continue

            jobs.append(
                self.make_job(
                    title=title,
                    company=job_company,
                    location=location,
                    apply_url=apply_url,
                    description=description,
                    platform="greenhouse",
                )
            )

        return jobs

    @staticmethod
    def extract_board_token(career_url: str) -> str:
        """Extract the Greenhouse board token from a public board URL."""
        candidate = career_url.strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        parts = [part for part in parsed.path.split("/") if part]

        if "greenhouse.io" not in host:
            raise ValueError(f"Not a Greenhouse career URL: {career_url}")
        if not parts:
            raise ValueError(f"Greenhouse board token not found in URL: {career_url}")
        if parts[0] in {"embed", "boards"} and len(parts) > 1:
            return parts[1]
        return parts[0]

    @staticmethod
    def _plain_text(value: str) -> str:
        """Convert an HTML job description into compact plain text."""
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()
