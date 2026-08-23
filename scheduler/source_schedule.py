"""Small scheduler-facing adapter for source manager runs."""

from __future__ import annotations

from typing import Iterable

from crawler.source_manager import JobSourceManager, SourceRun


def run_source_cycle(
    manager: JobSourceManager,
    *,
    query: str = "",
    sources: Iterable[str] | None = None,
) -> tuple[SourceRun, ...]:
    """Execute one isolated source cycle suitable for APScheduler jobs."""
    if not isinstance(manager, JobSourceManager):
        raise TypeError("manager must be a JobSourceManager")
    return tuple(manager.search_with_results(query, sources=sources))
