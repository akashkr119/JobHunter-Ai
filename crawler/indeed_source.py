"""Authorized Indeed job-source adapter.

This adapter does not automate Indeed login or scrape protected pages. It
accepts a caller-provided authorized integration client and normalizes its
results into the application's Job model.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from crawler.job_scraper import Job, JobScraper


class IndeedClient(Protocol):
    """Minimal contract for an authorized Indeed integration client."""

    def search_jobs(self, query: str = "", **kwargs: Any) -> Iterable[dict[str, Any]]:
        """Return job records obtained through an authorized integration."""


class IndeedSource:
    """Normalize jobs returned by an authorized Indeed integration."""

    name = "indeed"

    def __init__(self, client: IndeedClient | None = None) -> None:
        self.client = client

    def search(self, query: str = "", **kwargs: Any) -> list[Job]:
        if self.client is None:
            raise ValueError(
                "Indeed source requires an authorized integration client; "
                "Indeed login or protected-page scraping is not supported"
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
                        platform="indeed",
                    )
                )
            except (TypeError, ValueError):
                continue
        return jobs
