"""Workday ATS job scraper."""

from urllib.parse import urljoin, urlparse

import requests

from crawler.job_scraper import Job, JobScraper


class WorkdayScraper(JobScraper):
    """Fetch job listings from Workday's public careers endpoint."""

    def __init__(self, timeout: int = 20, page_size: int = 20, max_pages: int = 50) -> None:
        self.timeout = timeout
        self.page_size = page_size
        self.max_pages = max_pages

    def scrape(self, career_url: str, company: str = "") -> list[Job]:
        """Fetch and normalize jobs from a Workday careers URL."""
        career_url = self.validate_url(career_url)
        endpoint = self.build_jobs_endpoint(career_url)
        company_name = company.strip() or self._company_from_url(career_url)

        jobs: list[Job] = []
        offset = 0

        for _ in range(self.max_pages):
            response = requests.post(
                endpoint,
                json={"appliedFacets": {}, "limit": self.page_size, "offset": offset, "searchText": ""},
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "JobHunter-Ai/1.0",
                },
            )
            response.raise_for_status()
            payload = response.json()
            postings = payload.get("jobPostings") or []

            for item in postings:
                title = item.get("title", "")
                location = item.get("locationsText", "")
                external_path = item.get("externalPath", "")
                if not title or not external_path:
                    continue

                jobs.append(
                    self.make_job(
                        title=title,
                        company=company_name,
                        location=location,
                        apply_url=urljoin(career_url.rstrip("/") + "/", external_path.lstrip("/")),
                        platform="workday",
                    )
                )

            total = payload.get("total")
            offset += len(postings)
            if not postings or (isinstance(total, int) and offset >= total):
                break

        return self._deduplicate(jobs)

    @staticmethod
    def build_jobs_endpoint(career_url: str) -> str:
        """Build Workday's public jobs search endpoint from a careers URL."""
        parsed = urlparse(career_url)
        parts = [part for part in parsed.path.split("/") if part]

        try:
            locale_index = next(
                index for index, part in enumerate(parts)
                if len(part) == 5 and part[2] == "-"
            )
        except StopIteration:
            locale_index = -1

        if locale_index >= 0 and len(parts) > locale_index + 1:
            site = parts[locale_index + 1]
            prefix_parts = parts[:locale_index]
        elif parts:
            site = parts[-1]
            prefix_parts = parts[:-1]
        else:
            raise ValueError(f"Workday site name not found in URL: {career_url}")

        prefix = "/" + "/".join(prefix_parts) if prefix_parts else ""
        return f"{parsed.scheme}://{parsed.netloc}{prefix}/wday/cxs/{WorkdayScraper._tenant(parsed.netloc)}/{site}/jobs"

    @staticmethod
    def _tenant(hostname: str) -> str:
        """Infer the Workday tenant from the hostname."""
        host = (hostname or "").split(":", 1)[0].lower()
        first = host.split(".")[0]
        if first.startswith("wd") and "myworkdayjobs" in host:
            raise ValueError(
                "Workday tenant cannot be inferred from this hostname alone; "
                "use a careers URL that includes the tenant path."
            )
        return first

    @staticmethod
    def _company_from_url(career_url: str) -> str:
        host = (urlparse(career_url).hostname or "").lower()
        return host.split(".")[0] or "unknown"

    @staticmethod
    def _deduplicate(jobs: list[Job]) -> list[Job]:
        """Remove duplicate jobs using their apply URL."""
        unique: dict[str, Job] = {}
        for job in jobs:
            unique[job.apply_url] = job
        return list(unique.values())
