"""Adzuna API adapter for the unified JobSource interface."""

from __future__ import annotations

import os
from typing import Any, Iterable

import requests

from crawler.job_scraper import Job, JobScraper


class AdzunaSource:
    """Search Adzuna and return normalized Job objects.

    Credentials are read from environment variables so no API secret is stored
    in the repository. The source is deliberately independent from the
    scheduler and database; JobSourceManager can orchestrate it like any other
    source.
    """

    name = "adzuna"

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        country: str | None = None,
        session: requests.Session | None = None,
        timeout: float = 15,
    ) -> None:
        self.app_id = app_id or os.getenv("JOBHUNTER_ADZUNA_APP_ID")
        self.app_key = app_key or os.getenv("JOBHUNTER_ADZUNA_APP_KEY")
        self.country = (country or os.getenv("JOBHUNTER_ADZUNA_COUNTRY", "in")).strip().lower()
        self.session = session or requests.Session()
        self.timeout = timeout

    def search(self, query: str = "", **kwargs: Any) -> Iterable[Job]:
        if not self.app_id or not self.app_key:
            raise ValueError("Adzuna source requires JOBHUNTER_ADZUNA_APP_ID and JOBHUNTER_ADZUNA_APP_KEY")

        country = str(kwargs.get("country", self.country)).strip().lower()
        page = max(1, int(kwargs.get("page", 1)))
        results_per_page = max(1, min(50, int(kwargs.get("results_per_page", 20))))
        location = str(kwargs.get("location", "")).strip()
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": results_per_page,
        }
        if query.strip():
            params["what"] = query.strip()
        if location:
            params["where"] = location

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        return self._normalize(payload.get("results", ()))

    @staticmethod
    def _normalize(results: Iterable[dict[str, Any]]) -> list[Job]:
        jobs: list[Job] = []
        for item in results:
            if not isinstance(item, dict):
                # Provider payloads can contain null or otherwise malformed
                # records. Ignore those records without affecting valid jobs.
                continue
            try:
                company = item.get("company") or {}
                location = item.get("location") or {}
                jobs.append(
                    JobScraper.make_job(
                        title=item.get("title", ""),
                        company=company.get("display_name", "") if isinstance(company, dict) else str(company),
                        location=location.get("display_name", "") if isinstance(location, dict) else str(location),
                        apply_url=item.get("redirect_url", ""),
                        description=item.get("description", ""),
                        platform="adzuna",
                    )
                )
            except (TypeError, ValueError):
                # A malformed provider record must not discard valid listings.
                continue
        return jobs
