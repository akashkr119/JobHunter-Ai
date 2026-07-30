"""Basic Ashby job scraper."""

import requests

from crawler.job_scraper import Job, JobScraper


class AshbyScraper(JobScraper):
    """Scrape jobs from an Ashby careers API."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        jobs: list[Job] = []

        for item in data.get("jobs", []):
            jobs.append(
                Job(
                    title=item.get("title", ""),
                    company=item.get("organizationName", ""),
                    location=item.get("location", ""),
                    apply_url=item.get("jobUrl", "")
                )
            )

        return jobs
