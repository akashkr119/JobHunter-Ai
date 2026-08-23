"""Unified configuration for registered job sources."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class SourceConfig:
    """Runtime configuration shared by all job-source adapters."""

    enabled: tuple[str, ...] = ()
    disabled: tuple[str, ...] = ()
    retry_attempts: int = 1

    def __post_init__(self) -> None:
        if self.retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1")
        enabled = tuple(_normalize(self.enabled))
        disabled = tuple(_normalize(self.disabled))
        overlap = set(enabled) & set(disabled)
        if overlap:
            raise ValueError(f"Sources cannot be both enabled and disabled: {sorted(overlap)}")
        object.__setattr__(self, "enabled", enabled)
        object.__setattr__(self, "disabled", disabled)

    @classmethod
    def from_env(cls) -> "SourceConfig":
        """Load source selection without exposing provider credentials."""
        enabled = _csv(os.getenv("JOBHUNTER_SOURCES", ""))
        disabled = _csv(os.getenv("JOBHUNTER_DISABLED_SOURCES", ""))
        raw_attempts = os.getenv("JOBHUNTER_SOURCE_RETRY_ATTEMPTS", "1").strip()
        try:
            retry_attempts = int(raw_attempts)
        except ValueError as exc:
            raise ValueError("JOBHUNTER_SOURCE_RETRY_ATTEMPTS must be an integer") from exc
        return cls(enabled=enabled, disabled=disabled, retry_attempts=retry_attempts)

    def selected(self, available: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        """Return configured sources in registration order."""
        available_normalized = tuple(_normalize(available))
        if self.enabled:
            selected = tuple(name for name in self.enabled if name in available_normalized)
        else:
            selected = available_normalized
        disabled = set(self.disabled)
        return tuple(name for name in selected if name not in disabled)


def _normalize(values):
    seen = set()
    for value in values:
        name = str(value).strip().lower()
        if name and name not in seen:
            seen.add(name)
            yield name


def _csv(value: str) -> tuple[str, ...]:
    return tuple(_normalize(value.split(",")))
