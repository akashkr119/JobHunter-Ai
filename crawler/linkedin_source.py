"""Authorized LinkedIn job-source adapter.

This adapter intentionally does not automate LinkedIn login or scrape protected
pages. It accepts a caller-provided authorized integration client that exposes
search_jobs(query=..., **kwargs), then normalizes returned records into Job
objects.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from crawler.job_scraper import Job, JobScraper


class LinkedInClient(Protocol):
    """Minimal contract for an authorized LinkedIn integration client."""

    def search_jobs(self, query: str = "", **kwargs: Any) -> Iterable[dict[str, Any]]:
        """Return job records obtained through an authorized integration."""


class LinkedInSource:
    """Normalize jobs returned by an authorized LinkedIn integration."""

    name = "linkedin"

    def __init__(self, client: LinkedInClient | None = None) -> None:
        self.client = client

    def search(self, query: str = "", **kwargs: Any) -> list[Job]:
        if self.client is None:
            raise ValueError(
                "LinkedIn source requires an authorized integration client; "
                "LinkedIn login or protected-page scraping is not supported"
            )
        records = self.client.search_jobs(query=query, **kwargs)
        return self._normalize(records)

    @staticmethod
    def _normalize(records: Iterable[dict[str, Any]]) -> list[Job]:
        jobs: list[Job] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            try:
                jobs.append(
                    JobScraper.make_job(
                        title=record.get("title", ""),
                        company=record.get("company", ""),
                        location=record.get("location", ""),
                        apply_url=record.get("apply_url") or record.get("url", ""),
                        description=record.get("description", ""),
                        platform="linkedin",
                    )
                )
            except (TypeError, ValueError):
                continue
        return jobs
