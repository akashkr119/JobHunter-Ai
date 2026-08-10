"""Google Jobs source backed by the authorized SerpApi API."""

from __future__ import annotations

import os
from typing import Any

import requests

from crawler.job_scraper import Job, JobScraper
from crawler.job_source import JobSearchRequest, JobSource


class GoogleJobsSource(JobSource):
    """Discover jobs from Google's Jobs results through SerpApi.

    This adapter does not automate a Google or job-board session. It uses the
    documented SerpApi API and converts returned listings into the normalized
    application ``Job`` model.
    """

    name = "google_jobs"
    endpoint = "https://serpapi.com/search.json"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = str(api_key or os.getenv("JOBHUNTER_SERPAPI_KEY") or "").strip()
        self.session = session or requests.Session()
        self.timeout = float(timeout)
        if self.timeout <= 0:
            raise ValueError("Google Jobs timeout must be greater than zero")

    def search(self, request: JobSearchRequest) -> list[Job]:
        """Search Google Jobs and return normalized listings."""
        if not self.api_key:
            raise ValueError("SerpApi API key is required for Google Jobs")

        keywords = " ".join(k.strip() for k in request.keywords if k and k.strip())
        locations = [l.strip() for l in request.locations if l and l.strip()]
        query = keywords or "jobs"
        if not locations and request.remote:
            query = f"{query} remote"

        params: dict[str, Any] = {
            "engine": "google_jobs",
            "q": query,
            "api_key": self.api_key,
            "output": "json",
        }
        if locations:
            params["location"] = locations[0]
        if request.remote:
            params["ltype"] = "1"

        response = self.session.get(self.endpoint, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Google Jobs returned an invalid response")
        if payload.get("error"):
            raise RuntimeError(f"Google Jobs search failed: {payload['error']}")

        jobs: list[Job] = []
        for item in payload.get("jobs_results", [])[: request.limit]:
            job = self._parse_job(item)
            if job is not None:
                jobs.append(job)
        return jobs

    @staticmethod
    def _parse_job(item: Any) -> Job | None:
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        company = item.get("company_name")
        location = item.get("location") or ""
        description = item.get("description") or ""
        apply_url = item.get("share_link") or ""

        if not apply_url:
            for option in item.get("apply_options") or []:
                if isinstance(option, dict) and option.get("link"):
                    apply_url = str(option["link"]).strip()
                    break
        if not title or not company or not apply_url:
            return None

        try:
            return JobScraper.make_job(
                title=title,
                company=company,
                location=location,
                apply_url=apply_url,
                description=description,
                platform="google_jobs",
            )
        except ValueError:
            return None
