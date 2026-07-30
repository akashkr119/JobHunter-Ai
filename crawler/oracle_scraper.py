"""Basic Oracle Recruiting Cloud job scraper."""

import requests

from crawler.job_scraper import Job, JobScraper


class OracleScraper(JobScraper):
    """Scrape jobs from an Oracle Recruiting Cloud endpoint."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        jobs: list[Job] = []

        for item in data.get("items", []):
            jobs.append(
                Job(
                    title=item.get("title", ""),
                    company=item.get("organization", ""),
                    location=item.get("location", ""),
                    apply_url=item.get("applyUrl", "")
                )
            )

        return jobs
