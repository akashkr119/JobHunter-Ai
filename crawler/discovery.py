"""Unified discovery service for normalized multi-source job listings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from crawler.job_scraper import Job
from crawler.source_manager import JobSourceManager, SourceRun

_TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "referrer", "source", "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term"}


def canonical_url(url: str) -> str:
    """Normalize a job URL while preserving a meaningful trailing slash."""
    parts = urlsplit(str(url).strip())
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in _TRACKING_PARAMS]
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def _dedup_key(url: str) -> str:
    """Return a comparison key where equivalent trailing-slash URLs match."""
    value = canonical_url(url)
    parts = urlsplit(value)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


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
        grouped: dict[str, tuple[Job, list[str], str]] = {}
        for run in runs:
            for job in run.jobs:
                display_url = canonical_url(job.apply_url)
                key = _dedup_key(job.apply_url)
                if key not in grouped:
                    grouped[key] = (job, [run.source], display_url)
                else:
                    existing_job, source_names, existing_url = grouped[key]
                    if run.source not in source_names:
                        source_names.append(run.source)
                    if urlsplit(display_url).path.endswith("/") and not urlsplit(existing_url).path.endswith("/"):
                        existing_url = display_url
                    grouped[key] = (existing_job, source_names, existing_url)
        provenance = tuple(DiscoveryJob(job, tuple(source_names), display_url) for job, source_names, display_url in grouped.values())
        return DiscoveryResult(tuple(item.job for item in provenance), runs, provenance)
