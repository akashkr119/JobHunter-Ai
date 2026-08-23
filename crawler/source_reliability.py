"""Reliability tracking and bounded retry helpers for job sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SourceMetrics:
    source: str
    runs: int = 0
    successes: int = 0
    failures: int = 0
    jobs_returned: int = 0
    last_started_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error: str | None = None

    @property
    def success_rate(self) -> float:
        return round((self.successes / self.runs) * 100, 1) if self.runs else 0.0


class SourceReliabilityTracker:
    """In-memory operational history for source executions."""

    def __init__(self) -> None:
        self._metrics: dict[str, SourceMetrics] = {}

    def start(self, source: str) -> SourceMetrics:
        key = str(source).strip().lower()
        metric = self._metrics.setdefault(key, SourceMetrics(key))
        metric.runs += 1
        metric.last_started_at = _now()
        return metric

    def success(self, source: str, jobs_returned: int = 0) -> SourceMetrics:
        key = str(source).strip().lower()
        metric = self._metrics.setdefault(key, SourceMetrics(key))
        metric.successes += 1
        metric.jobs_returned += max(0, int(jobs_returned))
        metric.last_success_at = _now()
        metric.last_error = None
        return metric

    def failure(self, source: str, error: str) -> SourceMetrics:
        key = str(source).strip().lower()
        metric = self._metrics.setdefault(key, SourceMetrics(key))
        metric.failures += 1
        metric.last_failure_at = _now()
        metric.last_error = str(error)
        return metric

    def snapshot(self, sources: Iterable[str] | None = None) -> tuple[SourceMetrics, ...]:
        if sources is None:
            return tuple(self._metrics.values())
        return tuple(self._metrics[str(name).strip().lower()] for name in sources if str(name).strip().lower() in self._metrics)


def retry_call(operation: Callable[[], T], *, attempts: int = 2) -> T:
    """Retry a transient source operation a bounded number of times."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    assert last_error is not None
    raise last_error
