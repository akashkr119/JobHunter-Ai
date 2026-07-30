"""Basic Greenhouse job scraper."""

import requests

from crawler.job_scraper import Job, JobScraper


class GreenhouseScraper(JobScraper):
    """Scrape jobs from a Greenhouse board API."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        jobs: list[Job] = []

        for item in data.get("jobs", []):
            jobs.append(
                Job(
                    title=item.get("title", ""),
                    company="",
                    location=item.get("location", {}).get("name", ""),
                    apply_url=item.get("absolute_url", ""),
                )
            )

        return jobs
