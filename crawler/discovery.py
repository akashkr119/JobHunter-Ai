"""Unified discovery service for normalized multi-source job listings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from crawler.job_scraper import Job
from crawler.source_manager import JobSourceManager, SourceRun

_TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "referrer", "source", "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term"}


def canonical_url(url: str) -> str:
    """Normalize a job URL for stable cross-source comparison."""
    parts = urlsplit(str(url).strip())
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in _TRACKING_PARAMS]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


@dataclass(frozen=True)
class DiscoveryJob:
    job: Job
    sources: tuple[str, ...]
    canonical_url: str


@dataclass(frozen=True)
class DiscoveryResult:
    """Combined discovery response with source-level outcomes."""

    jobs: tuple[Job, ...]
    runs: tuple[SourceRun, ...]
    provenance: tuple[DiscoveryJob, ...] = ()

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
    """Run configured sources and return normalized, provenance-aware results."""

    def __init__(self, manager: JobSourceManager) -> None:
        self.manager = manager

    def discover(self, query: str = "", *, sources: Iterable[str] | None = None, **kwargs) -> DiscoveryResult:
        runs = tuple(self.manager.search_with_results(query, sources=sources, **kwargs))
        grouped: dict[str, tuple[Job, list[str]]] = {}
        for run in runs:
            for job in run.jobs:
                key = canonical_url(job.apply_url)
                if key not in grouped:
                    grouped[key] = (job, [run.source])
                elif run.source not in grouped[key][1]:
                    grouped[key][1].append(run.source)
        provenance = tuple(DiscoveryJob(job, tuple(source_names), key) for key, (job, source_names) in grouped.items())
        return DiscoveryResult(tuple(item.job for item in provenance), runs, provenance)
