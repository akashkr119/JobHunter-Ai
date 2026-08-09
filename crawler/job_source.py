"""Common interfaces for multi-source job discovery.

A source adapter is responsible for obtaining jobs from one authorized source
and returning the application's normalized :class:`Job` model. The manager
keeps source-specific concerns out of the rest of the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable

from crawler.job_scraper import Job


@dataclass(frozen=True)
class JobSearchRequest:
    """Normalized search input passed to every job source."""

    keywords: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    remote: bool = False
    limit: int = 50
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("Job search limit must be greater than zero")


class JobSource(ABC):
    """Contract implemented by every job-discovery source adapter."""

    name = "unknown"

    @property
    def source_name(self) -> str:
        """Stable identifier used in logs, persistence, and analytics."""
        return self.name

    @abstractmethod
    def search(self, request: JobSearchRequest) -> list[Job]:
        """Return normalized jobs for the supplied search request."""
        raise NotImplementedError


class JobSourceManager:
    """Register and query multiple job sources without source coupling."""

    def __init__(self, sources: Iterable[JobSource] | None = None) -> None:
        self._sources: dict[str, JobSource] = {}
        for source in sources or ():
            self.register(source)

    def register(self, source: JobSource) -> None:
        """Register a source by its stable name."""
        if not isinstance(source, JobSource):
            raise TypeError("source must implement JobSource")
        name = source.source_name.strip().lower()
        if not name:
            raise ValueError("Job source name cannot be empty")
        if name in self._sources:
            raise ValueError(f"Job source already registered: {name}")
        self._sources[name] = source

    def get(self, name: str) -> JobSource:
        """Return a registered source by name."""
        key = str(name or "").strip().lower()
        try:
            return self._sources[key]
        except KeyError as exc:
            raise KeyError(f"Unknown job source: {name}") from exc

    def names(self) -> tuple[str, ...]:
        """Return registered source names in registration order."""
        return tuple(self._sources)

    def search(
        self,
        request: JobSearchRequest,
        sources: Iterable[str] | None = None,
    ) -> list[Job]:
        """Search selected sources and isolate source failures.

        A single unavailable source must not prevent other sources from
        returning jobs. The source adapter remains responsible for logging
        its detailed failure; this method intentionally returns successful
        results only.
        """
        selected = list(sources) if sources is not None else list(self._sources)
        jobs: list[Job] = []
        for name in selected:
            source = self.get(name)
            try:
                jobs.extend(source.search(request))
            except Exception:
                continue
        return jobs
