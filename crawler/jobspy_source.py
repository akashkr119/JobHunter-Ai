"""JobSpy-backed multi-platform job-board source.

JobSpy provides one normalized search interface for public job-board listings
from LinkedIn, Indeed, Naukri and several other boards. This adapter keeps the
rest of JobHunter AI independent from the provider's DataFrame representation.

The adapter never performs a login or uses a user's credentials. Providers may
still rate-limit or block automated requests; source failures are isolated by
JobSourceManager so another board can continue to return jobs.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

from crawler.job_scraper import Job, JobScraper


class JobSpySource:
    """Search one JobSpy-supported public job board."""

    def __init__(self, site_name: str) -> None:
        self.name = str(site_name).strip().lower()
        if not self.name:
            raise ValueError("JobSpy source name cannot be empty")

    def search(self, query: str = "", **kwargs: Any) -> Iterable[Job]:
        try:
            from jobspy import scrape_jobs
        except ImportError as exc:
            raise RuntimeError(
                "JobSpy is not installed. Install python-jobspy before discovery."
            ) from exc

        location = str(kwargs.get("location", "")).strip() or None
        results_wanted = max(1, min(50, int(kwargs.get("results_wanted", 25))))
        hours_old = kwargs.get("hours_old")
        country_indeed = str(kwargs.get("country_indeed", "India")).strip() or "India"
        is_remote = bool(kwargs.get("is_remote", False))

        params: dict[str, Any] = {
            "site_name": self.name,
            "search_term": str(query or "").strip() or None,
            "location": location,
            "results_wanted": results_wanted,
            "country_indeed": country_indeed,
            "linkedin_fetch_description": False,
            "verbose": 0,
        }
        if hours_old is not None:
            params["hours_old"] = max(1, int(hours_old))
        if is_remote:
            params["is_remote"] = True
        if self.name == "google" and query:
            where = f" near {location}" if location else ""
            params["google_search_term"] = f"{query} jobs{where}"

        frame = scrape_jobs(**params)
        if frame is None or getattr(frame, "empty", True):
            return []

        return self._normalize(frame.to_dict("records"))

    def _normalize(self, records: Iterable[dict[str, Any]]) -> list[Job]:
        jobs: list[Job] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            title = _text(record.get("title"))
            company = _text(record.get("company"))
            location = _location(record)
            apply_url = _text(record.get("job_url_direct")) or _text(record.get("job_url"))
            description = _text(record.get("description"))
            if not title or not company or not apply_url:
                continue
            try:
                jobs.append(
                    JobScraper.make_job(
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        description=description,
                        platform=self.name,
                    )
                )
            except (TypeError, ValueError):
                continue
        return jobs


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def _location(record: dict[str, Any]) -> str:
    direct = _text(record.get("location"))
    if direct:
        return direct
    parts = [_text(record.get("city")), _text(record.get("state")), _text(record.get("country"))]
    return ", ".join(part for part in parts if part)
