"""Basic Workday job scraper."""

from bs4 import BeautifulSoup
import requests

from crawler.job_scraper import Job, JobScraper


class WorkdayScraper(JobScraper):
    """Scrape job listings from a Workday careers page."""

    def scrape(self, career_url: str) -> list[Job]:
        response = requests.get(career_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        jobs: list[Job] = []

        for link in soup.find_all("a", href=True):
            title = link.get_text(strip=True)
            href = link["href"]
            if title and "/job/" in href:
                jobs.append(
                    Job(
                        title=title,
                        company="",
                        location="",
                        apply_url=href,
                    )
                )

        return jobs
