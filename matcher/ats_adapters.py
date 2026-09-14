"""Supported ATS submission adapter boundaries.

These adapters deliberately do not automate browsers, bypass authentication,
CAPTCHAs, or platform controls. A caller must provide an authorized transport
for the supported ATS flow; the adapter only validates that the application
URL belongs to the expected ATS and forwards the already-approved package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from matcher.application_package import ApplicationPackage


class UnsupportedATSUrlError(ValueError):
    """Raised when a package URL is not a supported ATS URL for the adapter."""


Transport = Callable[[ApplicationPackage], str]


@dataclass(frozen=True)
class ATSSubmissionAdapter:
    """Safe adapter boundary for one supported ATS host family."""

    platform: str
    allowed_hosts: tuple[str, ...]
    transport: Transport

    def submit(self, package: ApplicationPackage) -> str:
        parsed = urlparse(package.apply_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise UnsupportedATSUrlError("Supported ATS submissions require an HTTPS URL")
        hostname = parsed.hostname.lower()
        if not any(hostname == host or hostname.endswith("." + host) for host in self.allowed_hosts):
            raise UnsupportedATSUrlError(
                f"Application URL is not a supported {self.platform} application flow"
            )
        return str(self.transport(package))


class GreenhouseAdapter(ATSSubmissionAdapter):
    def __init__(self, transport: Transport) -> None:
        super().__init__("Greenhouse", ("greenhouse.io", "boards.greenhouse.io"), transport)


class LeverAdapter(ATSSubmissionAdapter):
    def __init__(self, transport: Transport) -> None:
        super().__init__("Lever", ("lever.co", "jobs.lever.co"), transport)


class WorkdayAdapter(ATSSubmissionAdapter):
    def __init__(self, transport: Transport) -> None:
        super().__init__("Workday", ("myworkdayjobs.com",), transport)


class SmartRecruitersAdapter(ATSSubmissionAdapter):
    def __init__(self, transport: Transport) -> None:
        super().__init__("SmartRecruiters", ("smartrecruiters.com", "jobs.smartrecruiters.com"), transport)


def adapter_for_platform(platform: str, transport: Transport) -> ATSSubmissionAdapter:
    """Build a supported ATS adapter without performing any external action."""
    normalized = str(platform).strip().lower()
    adapters = {
        "greenhouse": GreenhouseAdapter,
        "lever": LeverAdapter,
        "workday": WorkdayAdapter,
        "smartrecruiters": SmartRecruitersAdapter,
    }
    try:
        return adapters[normalized](transport)
    except KeyError as exc:
        raise ValueError(f"Unsupported ATS platform: {platform}") from exc
