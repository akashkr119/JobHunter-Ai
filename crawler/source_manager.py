"""Unified job-source orchestration.

The source manager deliberately keeps external job providers behind a small
adapter interface.  Existing ATS/career-page scrapers can be registered as
sources now, while API-backed or permitted platform adapters (LinkedIn,
Indeed, Naukri, etc.) can be added later without changing matching/database
code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from crawler.job_scraper import Job


class JobSource(Protocol):
    """Contract implemented by every job-discovery source."""

    name: str

    def search(self, query: str = "", **kwargs) -> Iterable[Job]:
        """Return normalized jobs for the requested search."""


@dataclass(frozen=True)
class SourceRun:
    """Result of running one source."""

    source: str
    jobs: tuple[Job, ...]
    error: str | None = None


class JobSourceManager:
    """Register, select and run job sources behind one stable API."""

    def __init__(self, sources: Iterable[JobSource] | None = None) -> None:
        self._sources: dict[str, JobSource] = {}
        for source in sources or ():
            self.register(source)

    def register(self, source: JobSource) -> None:
        """Register a source by its stable, case-insensitive name."""
        name = str(getattr(source, "name", "")).strip().lower()
        if not name:
            raise ValueError("Job source name cannot be empty")
        if not callable(getattr(source, "search", None)):
            raise ValueError(f"Job source {name!r} must implement search()")
        self._sources[name] = source

    def unregister(self, name: str) -> None:
        """Remove a source if it is registered."""
        self._sources.pop(str(name).strip().lower(), None)

    def names(self) -> tuple[str, ...]:
        """Return registered source names in deterministic order."""
        return tuple(sorted(self._sources))

    def get(self, name: str) -> JobSource:
        """Return a registered source or raise a useful error."""
        key = str(name).strip().lower()
        try:
            return self._sources[key]
        except KeyError as exc:
            available = ", ".join(self.names()) or "none"
            raise ValueError(f"Unknown job source: {name!r}. Available: {available}") from exc

    def search(self, query: str = "", sources: Iterable[str] | None = None, **kwargs) -> list[Job]:
        """Run selected sources and return one normalized, de-duplicated list.

        A source failure is isolated so one unavailable provider cannot prevent
        the remaining providers from returning jobs.  Errors are exposed via
        :meth:`search_with_results` when callers need diagnostics.
        """
        return [job for result in self.search_with_results(query, sources=sources, **kwargs) for job in result.jobs]

    def search_with_results(self, query: str = "", sources: Iterable[str] | None = None, **kwargs) -> list[SourceRun]:
        """Run selected sources while preserving per-source success/failure."""
        selected = self.names() if sources is None else tuple(str(name).strip().lower() for name in sources)
        results: list[SourceRun] = []
        for name in selected:
            source = self.get(name)
            try:
                jobs = tuple(source.search(query, **kwargs) or ())
                results.append(SourceRun(name, jobs))
            except Exception as exc:  # noqa: BLE001 - source isolation is intentional
                results.append(SourceRun(name, (), f"{type(exc).__name__}: {exc}"))
        return results

    @staticmethod
    def deduplicate(jobs: Iterable[Job]) -> list[Job]:
        """Deduplicate normalized jobs by apply URL while preserving order."""
        seen: set[str] = set()
        unique: list[Job] = []
        for job in jobs:
            key = str(job.apply_url).strip().rstrip("/").lower()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(job)
        return unique


class CallableJobSource:
    """Small adapter for turning a function into a :class:`JobSource`."""

    def __init__(self, name: str, search: Callable[..., Iterable[Job]]) -> None:
        self.name = name
        self._search = search

    def search(self, query: str = "", **kwargs) -> Iterable[Job]:
        return self._search(query=query, **kwargs)
