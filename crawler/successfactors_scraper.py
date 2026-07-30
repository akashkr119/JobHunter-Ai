"""Basic SAP SuccessFactors job scraper."""

import requests

from crawler.job_scraper import Job, JobScraper


class SuccessFactorsScraper(JobScraper):
    """Scrape jobs from a SAP SuccessFactors careers endpoint."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        jobs: list[Job] = []

        for item in data.get("jobs", []):
            jobs.append(
                Job(
                    title=item.get("title", ""),
                    company=item.get("company", ""),
                    location=item.get("location", ""),
                    apply_url=item.get("jobUrl", "")
                )
            )

        return jobs
