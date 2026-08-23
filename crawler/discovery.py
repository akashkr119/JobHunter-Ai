"""Unified discovery service for normalized multi-source job listings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from crawler.job_scraper import Job
from crawler.source_manager import JobSourceManager, SourceRun


@dataclass(frozen=True)
class DiscoveryResult:
    """Combined discovery response with source-level outcomes."""

    jobs: tuple[Job, ...]
    runs: tuple[SourceRun, ...]

    @property
    def failed_sources(self) -> tuple[str, ...]:
        return tuple(run.source for run in self.runs if run.error)

    @property
    def source_count(self) -> int:
        return len(self.runs)

    @property
    def job_count(self) -> int:
        return len(self.jobs)


class JobDiscovery:
    """Run configured sources and return one normalized discovery result."""

    def __init__(self, manager: JobSourceManager) -> None:
        self.manager = manager

    def discover(
        self,
        query: str = "",
        *,
        sources: Iterable[str] | None = None,
        **kwargs,
    ) -> DiscoveryResult:
        runs = tuple(self.manager.search_with_results(query, sources=sources, **kwargs))
        jobs = tuple(self.manager.deduplicate(job for run in runs for job in run.jobs))
        return DiscoveryResult(jobs=jobs, runs=runs)
