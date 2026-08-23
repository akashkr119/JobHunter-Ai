"""Unified job-source orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from crawler.job_scraper import Job
from crawler.source_health import SourceHealth, SourceStatus


class JobSource(Protocol):
    name: str

    def search(self, query: str = "", **kwargs) -> Iterable[Job]:
        """Return normalized jobs for the requested search."""


@dataclass(frozen=True)
class SourceRun:
    source: str
    jobs: tuple[Job, ...]
    error: str | None = None

    @property
    def status(self) -> SourceStatus:
        return SourceStatus.FAILED if self.error else SourceStatus.AVAILABLE

    def health(self) -> SourceHealth:
        return SourceHealth(self.source, self.status, self.error)


class JobSourceManager:
    """Register, select and run job sources behind one stable API."""

    def __init__(self, sources: Iterable[JobSource] | None = None) -> None:
        self._sources: dict[str, JobSource] = {}
        for source in sources or ():
            self.register(source)

    @classmethod
    def with_builtin_sources(cls, *, adzuna=None, linkedin=None, indeed=None, naukri=None) -> "JobSourceManager":
        manager = cls()
        for source in (adzuna, linkedin, indeed, naukri):
            if source is not None:
                manager.register(source)
        return manager

    def register(self, source: JobSource) -> None:
        name = str(getattr(source, "name", "")).strip().lower()
        if not name:
            raise ValueError("Job source name cannot be empty")
        if not callable(getattr(source, "search", None)):
            raise ValueError(f"Job source {name!r} must implement search()")
        self._sources[name] = source

    def unregister(self, name: str) -> None:
        self._sources.pop(str(name).strip().lower(), None)

    def names(self) -> tuple[str, ...]:
        return tuple(self._sources)

    def get(self, name: str) -> JobSource:
        key = str(name).strip().lower()
        try:
            return self._sources[key]
        except KeyError as exc:
            available = ", ".join(self.names()) or "none"
            raise ValueError(f"Unknown job source: {name!r}. Available: {available}") from exc

    def search(self, query: str = "", sources: Iterable[str] | None = None, **kwargs) -> list[Job]:
        jobs = [job for result in self.search_with_results(query, sources=sources, **kwargs) for job in result.jobs]
        return self.deduplicate(jobs)

    def search_with_results(self, query: str = "", sources: Iterable[str] | None = None, **kwargs) -> list[SourceRun]:
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

    def health(self, sources: Iterable[str] | None = None) -> tuple[SourceHealth, ...]:
        """Run selected sources and expose operational health alongside jobs."""
        return tuple(result.health() for result in self.search_with_results(sources=sources))

    @staticmethod
    def deduplicate(jobs: Iterable[Job]) -> list[Job]:
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
    def __init__(self, name: str, search: Callable[..., Iterable[Job]]) -> None:
        self.name = name
        self._search = search

    def search(self, query: str = "", **kwargs) -> Iterable[Job]:
        return self._search(query=query, **kwargs)
