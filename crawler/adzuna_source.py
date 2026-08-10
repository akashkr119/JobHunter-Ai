"""Authorized Adzuna API adapter for multi-source job discovery."""

from __future__ import annotations

import os
from urllib.parse import urlencode

import requests

from crawler.job_scraper import Job, JobScraper
from crawler.job_source import JobSearchRequest, JobSource


class AdzunaSource(JobSource):
    """Search Adzuna's public API and normalize results into ``Job`` objects."""

    name = "adzuna"
    base_url = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id: str | None = None, app_key: str | None = None, country: str = "in", session: requests.Session | None = None, timeout: float = 15.0) -> None:
        self.app_id = app_id or os.getenv("JOBHUNTER_ADZUNA_APP_ID")
        self.app_key = app_key or os.getenv("JOBHUNTER_ADZUNA_APP_KEY")
        self.country = country.strip().lower() or "in"
        self.session = session or requests.Session()
        self.timeout = timeout

    def search(self, request: JobSearchRequest) -> list[Job]:
        """Return normalized Adzuna results for the requested keywords/locations."""
        if not self.app_id or not self.app_key:
            raise RuntimeError("Adzuna source requires JOBHUNTER_ADZUNA_APP_ID and JOBHUNTER_ADZUNA_APP_KEY")
        keywords = " ".join(k.strip() for k in request.keywords if k.strip()).strip()
        if not keywords:
            raise ValueError("Adzuna search requires at least one keyword")
        params = {"app_id": self.app_id, "app_key": self.app_key, "results_per_page": min(request.limit, 50), "what": keywords, "content-type": "application/json"}
        if request.locations:
            params["where"] = ", ".join(x.strip() for x in request.locations if x.strip())
        if request.remote:
            params["what_and"] = "remote"
        url = f"{self.base_url}/{self.country}/search/1?{urlencode(params)}"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        jobs: list[Job] = []
        for item in payload.get("results", [])[: request.limit]:
            try:
                jobs.append(self._normalize(item))
            except (KeyError, TypeError, ValueError):
                continue
        return jobs

    @staticmethod
    def _normalize(item: dict) -> Job:
        company = (item.get("company") or {}).get("display_name") or "Unknown company"
        location = (item.get("location") or {}).get("display_name", "")
        return JobScraper.make_job(
            title=item.get("title", ""),
            company=company,
            location=location,
            apply_url=item.get("redirect_url", ""),
            description=item.get("description", ""),
            platform="adzuna",
        )
