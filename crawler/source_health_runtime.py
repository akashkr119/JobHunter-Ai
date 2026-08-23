"""Bridge live JobSourceManager health into dashboard configuration."""

from __future__ import annotations

from typing import Any


def source_health_provider(manager: Any):
    """Return a dashboard-compatible provider backed by a source manager."""
    if manager is None or not callable(getattr(manager, "health", None)):
        raise ValueError("A JobSourceManager with health() is required")

    def provider():
        return manager.health()

    return provider
