"""Authorized Jooble REST API adapter for multi-source job discovery."""

from __future__ import annotations

import os

import requests

from crawler.job_scraper import Job, JobScraper
from crawler.job_source import JobSearchRequest, JobSource


class JoobleSource(JobSource):
    """Search Jooble's REST API and normalize results into ``Job`` objects."""

    name = "jooble"
    base_url = "https://jooble.org/api"

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.getenv("JOBHUNTER_JOOBLE_API_KEY")
        self.session = session or requests.Session()
        self.timeout = timeout

    def search(self, request: JobSearchRequest) -> list[Job]:
        if not self.api_key:
            raise RuntimeError("Jooble source requires JOBHUNTER_JOOBLE_API_KEY")
        keywords = ", ".join(k.strip() for k in request.keywords if k.strip())
        if not keywords:
            raise ValueError("Jooble search requires at least one keyword")
        locations = list(x.strip() for x in request.locations if x.strip())
        location = ", ".join(locations) if locations else ""
        payload = {
            "keywords": keywords,
            "location": location,
            "page": 1,
            "ResultOnPage": min(request.limit, 100),
            "companysearch": False,
        }
        response = self.session.post(
            f"{self.base_url}/{self.api_key}",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        jobs: list[Job] = []
        for item in data.get("jobs", [])[: request.limit]:
            try:
                jobs.append(self._normalize(item))
            except (KeyError, TypeError, ValueError):
                continue
        return jobs

    @staticmethod
    def _normalize(item: dict) -> Job:
        return JobScraper.make_job(
            title=item.get("title", ""),
            company=item.get("company", "Unknown company"),
            location=item.get("location", ""),
            apply_url=item.get("link", ""),
            description=item.get("snippet", ""),
            platform="jooble",
        )
