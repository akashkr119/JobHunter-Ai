"""Unified job-source orchestration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
import os
from typing import Callable, Iterable, Protocol

from crawler.job_scraper import Job
from crawler.source_config import SourceConfig
from crawler.source_health import SourceHealth, SourceStatus
from crawler.source_reliability import SourceMetrics, SourceReliabilityTracker, retry_call


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
    """Register, select, retry and run job sources behind one stable API.

    Sources are network-bound, so discovery runs them concurrently. A slow or
    blocked provider is bounded by a per-discovery timeout and is reported as a
    failed source instead of delaying successful providers.
    """

    DEFAULT_SOURCE_TIMEOUT_SECONDS = 30.0

    def __init__(
        self,
        sources: Iterable[JobSource] | None = None,
        *,
        retry_attempts: int = 1,
        tracker: SourceReliabilityTracker | None = None,
        config: SourceConfig | None = None,
        source_timeout_seconds: float | None = None,
        max_workers: int | None = None,
    ) -> None:
        self.config = config or SourceConfig(retry_attempts=retry_attempts)
        self.retry_attempts = self.config.retry_attempts
        self.source_timeout_seconds = self._read_timeout(source_timeout_seconds)
        self.max_workers = self._read_max_workers(max_workers)
        self._sources: dict[str, JobSource] = {}
        self.tracker = tracker or SourceReliabilityTracker()
        for source in sources or ():
            self.register(source)

    @classmethod
    def with_builtin_sources(cls, *, adzuna=None, linkedin=None, indeed=None, naukri=None, retry_attempts: int = 1, config: SourceConfig | None = None) -> "JobSourceManager":
        manager = cls(retry_attempts=retry_attempts, config=config)
        for source in (adzuna, linkedin, indeed, naukri):
            if source is not None:
                manager.register(source)
        return manager

    @staticmethod
    def _read_timeout(value: float | None) -> float:
        raw = os.getenv("JOBHUNTER_SOURCE_TIMEOUT_SECONDS", "").strip() if value is None else str(value)
        if not raw:
            return JobSourceManager.DEFAULT_SOURCE_TIMEOUT_SECONDS
        try:
            timeout = float(raw)
        except ValueError as exc:
            raise ValueError("JOBHUNTER_SOURCE_TIMEOUT_SECONDS must be numeric") from exc
        if timeout <= 0:
            raise ValueError("JOBHUNTER_SOURCE_TIMEOUT_SECONDS must be greater than 0")
        return timeout

    @staticmethod
    def _read_max_workers(value: int | None) -> int | None:
        raw = os.getenv("JOBHUNTER_SOURCE_MAX_WORKERS", "").strip() if value is None else str(value)
        if not raw:
            return None
        try:
            workers = int(raw)
        except ValueError as exc:
            raise ValueError("JOBHUNTER_SOURCE_MAX_WORKERS must be an integer") from exc
        if workers < 1:
            raise ValueError("JOBHUNTER_SOURCE_MAX_WORKERS must be at least 1")
        return workers

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

    def selected_names(self) -> tuple[str, ...]:
        return self.config.selected(self.names())

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

    def _run_source(self, name: str, query: str, kwargs: dict) -> tuple[tuple[Job, ...], str | None]:
        source = self.get(name)
        try:
            jobs = tuple(retry_call(lambda: source.search(query, **kwargs) or (), attempts=self.retry_attempts))
            return jobs, None
        except Exception as exc:  # noqa: BLE001 - source isolation is intentional
            return (), f"{type(exc).__name__}: {exc}"

    def search_with_results(self, query: str = "", sources: Iterable[str] | None = None, **kwargs) -> list[SourceRun]:
        selected = self.selected_names() if sources is None else tuple(str(name).strip().lower() for name in sources)
        if not selected:
            return []

        for name in selected:
            self.get(name)
            self.tracker.start(name)

        workers = self.max_workers or len(selected)
        workers = max(1, min(workers, len(selected)))
        executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="jobhunter-source")
        futures = {
            executor.submit(self._run_source, name, query, dict(kwargs)): name
            for name in selected
        }
        done, not_done = wait(tuple(futures), timeout=self.source_timeout_seconds)

        results: dict[str, SourceRun] = {}
        for future in done:
            name = futures[future]
            try:
                jobs, error = future.result()
            except Exception as exc:  # noqa: BLE001 - final source isolation guard
                jobs, error = (), f"{type(exc).__name__}: {exc}"
            if error:
                self.tracker.failure(name, error)
                results[name] = SourceRun(name, (), error)
            else:
                self.tracker.success(name, len(jobs))
                results[name] = SourceRun(name, jobs)

        for future in not_done:
            name = futures[future]
            error = f"TimeoutError: source exceeded {self.source_timeout_seconds:.1f}s timeout"
            self.tracker.failure(name, error)
            results[name] = SourceRun(name, (), error)
            future.cancel()

        # Do not wait for a blocked provider after the useful results are ready.
        # The running provider thread may finish later, but it can no longer hold
        # up the dashboard request or discard results from other providers.
        executor.shutdown(wait=False, cancel_futures=True)
        return [results[name] for name in selected]

    def health(self, sources: Iterable[str] | None = None) -> tuple[SourceHealth, ...]:
        return tuple(result.health() for result in self.search_with_results(sources=sources))

    def reliability(self, sources: Iterable[str] | None = None) -> tuple[SourceMetrics, ...]:
        return self.tracker.snapshot(sources)

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
