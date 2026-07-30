"""Basic SmartRecruiters job scraper."""

import requests

from crawler.job_scraper import Job, JobScraper


class SmartRecruitersScraper(JobScraper):
    """Scrape jobs from the SmartRecruiters API."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        jobs: list[Job] = []

        for item in data.get("content", []):
            jobs.append(Job(
                title=item.get("name", ""),
                company=item.get("company", ""),
                location=item.get("location", {}).get("city", ""),
                apply_url=item.get("ref", "")
            ))

        return jobs
