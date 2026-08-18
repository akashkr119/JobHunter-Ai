"""Operational health state for configured job sources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class SourceStatus(str, Enum):
    CONFIGURED = "configured"
    AVAILABLE = "available"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass(frozen=True)
class SourceHealth:
    """Current operational state of one job source."""

    source: str
    status: SourceStatus
    message: str | None = None


def evaluate_source_health(
    configured_sources: Iterable[str],
    results: Iterable[tuple[str, bool, str | None]],
    disabled_sources: Iterable[str] = (),
) -> tuple[SourceHealth, ...]:
    """Convert source execution results into deterministic health records."""
    disabled = {str(name).strip().lower() for name in disabled_sources}
    result_map = {
        str(name).strip().lower(): (ok, message)
        for name, ok, message in results
    }
    health: list[SourceHealth] = []
    for raw_name in configured_sources:
        name = str(raw_name).strip().lower()
        if not name:
            continue
        if name in disabled:
            health.append(SourceHealth(name, SourceStatus.DISABLED))
        elif name not in result_map:
            health.append(SourceHealth(name, SourceStatus.CONFIGURED))
        else:
            ok, message = result_map[name]
            health.append(
                SourceHealth(
                    name,
                    SourceStatus.AVAILABLE if ok else SourceStatus.FAILED,
                    None if ok else message,
                )
            )
    return tuple(health)
