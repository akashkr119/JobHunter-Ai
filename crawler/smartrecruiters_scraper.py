"""SmartRecruiters ATS job scraper."""

from urllib.parse import urlparse

import requests

from crawler.job_scraper import Job, JobScraper


class SmartRecruitersScraper(JobScraper):
    """Fetch public jobs from the SmartRecruiters postings API."""

    API_TEMPLATE = "https://api.smartrecruiters.com/v1/companies/{company_id}/postings"

    def __init__(self, timeout: int = 20, page_size: int = 100, max_pages: int = 50) -> None:
        self.timeout = timeout
        self.page_size = page_size
        self.max_pages = max_pages

    def scrape(self, career_url: str, company: str = "") -> list[Job]:
        """Fetch and normalize jobs from a SmartRecruiters company URL."""
        career_url = self.validate_url(career_url)
        company_id = self.extract_company_id(career_url)
        endpoint = self.API_TEMPLATE.format(company_id=company_id)

        jobs: list[Job] = []
        offset = 0

        for _ in range(self.max_pages):
            response = requests.get(
                endpoint,
                params={"limit": self.page_size, "offset": offset},
                timeout=self.timeout,
                headers={"User-Agent": "JobHunter-Ai/1.0"},
            )
            response.raise_for_status()
            payload = response.json()
            postings = payload.get("content") or []

            for item in postings:
                title = item.get("name", "")
                location = self._location(item.get("location") or {})
                apply_url = item.get("ref", "")
                job_company = company.strip() or self._company_name(item, company_id)

                if not title or not apply_url:
                    continue

                jobs.append(
                    self.make_job(
                        title=title,
                        company=job_company,
                        location=location,
                        apply_url=apply_url,
                        platform="smartrecruiters",
                    )
                )

            total = payload.get("totalFound")
            offset += len(postings)
            if not postings or (isinstance(total, int) and offset >= total):
                break

        return self._deduplicate(jobs)

    @staticmethod
    def extract_company_id(career_url: str) -> str:
        """Extract a SmartRecruiters company identifier from a public/API URL."""
        candidate = career_url.strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        parts = [part for part in parsed.path.split("/") if part]

        if "smartrecruiters.com" not in host:
            raise ValueError(f"Not a SmartRecruiters URL: {career_url}")

        if host == "api.smartrecruiters.com":
            if len(parts) >= 3 and parts[0] == "v1" and parts[1] == "companies":
                return parts[2]
            raise ValueError(f"SmartRecruiters company id not found in URL: {career_url}")

        if not parts:
            raise ValueError(f"SmartRecruiters company id not found in URL: {career_url}")

        return parts[0]

    @staticmethod
    def _location(location: dict) -> str:
        """Build a readable location from SmartRecruiters location fields."""
        values = [
            location.get("city", ""),
            location.get("region", ""),
            location.get("country", ""),
        ]
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            value = str(value or "").strip()
            if value and value.lower() not in seen:
                seen.add(value.lower())
                result.append(value)
        return ", ".join(result)

    @staticmethod
    def _company_name(item: dict, fallback: str) -> str:
        company = item.get("company")
        if isinstance(company, dict):
            return str(company.get("name") or company.get("identifier") or fallback).strip()
        if company:
            return str(company).strip()
        return fallback

    @staticmethod
    def _deduplicate(jobs: list[Job]) -> list[Job]:
        unique: dict[str, Job] = {}
        for job in jobs:
            unique[job.apply_url] = job
        return list(unique.values())
