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
        career_url = self.validate_url(career_url)
        company_id = self.extract_company_id(career_url)
        endpoint = self.API_TEMPLATE.format(company_id=company_id)
        jobs: list[Job] = []
        offset = 0

        for _ in range(self.max_pages):
            response = requests.get(endpoint, params={"limit": self.page_size, "offset": offset}, timeout=self.timeout, headers={"User-Agent": "JobHunter-Ai/1.0"})
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
                description = self._fetch_description(company_id, item)
                jobs.append(self.make_job(title=title, company=job_company, location=location, apply_url=apply_url, description=description, platform="smartrecruiters"))
            total = payload.get("totalFound")
            offset += len(postings)
            if not postings or (isinstance(total, int) and offset >= total):
                break
        return self._deduplicate(jobs)

    def _fetch_description(self, company_id: str, item: dict) -> str:
        """Fetch full posting details when a posting identifier is available."""
        posting_id = item.get("id") or item.get("uuid")
        if not posting_id:
            return self.combine_description(item.get("jobAd", ""), item.get("description", ""))
        url = f"{self.API_TEMPLATE.format(company_id=company_id)}/{posting_id}"
        try:
            response = requests.get(url, timeout=self.timeout, headers={"User-Agent": "JobHunter-Ai/1.0"})
            response.raise_for_status()
            detail = response.json()
        except requests.RequestException:
            return self.combine_description(item.get("jobAd", ""), item.get("description", ""))
        sections = detail.get("jobAd") or {}
        if isinstance(sections, dict):
            section_values = []
            for value in sections.values():
                if isinstance(value, dict):
                    section_values.extend(value.values())
                else:
                    section_values.append(value)
            return self.combine_description(*section_values, detail.get("description", ""))
        return self.combine_description(sections, detail.get("description", ""))

    @staticmethod
    def extract_company_id(career_url: str) -> str:
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
        values = [location.get("city", ""), location.get("region", ""), location.get("country", "")]
        seen, result = set(), []
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
        return str(company or fallback).strip()

    @staticmethod
    def _deduplicate(jobs: list[Job]) -> list[Job]:
        return list({job.apply_url: job for job in jobs}.values())
