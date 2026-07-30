"""Basic Lever job scraper."""

import requests

from crawler.job_scraper import Job, JobScraper


class LeverScraper(JobScraper):
    """Scrape jobs from a Lever postings API."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        postings = response.json()
        jobs: list[Job] = []

        for item in postings:
            jobs.append(
                Job(
                    title=item.get("text", ""),
                    company="",
                    location=item.get("categories", {}).get("location", ""),
                    apply_url=item.get("hostedUrl", ""),
                )
            )

        return jobs
