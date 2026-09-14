"""Tests for supported, non-bypassing ATS adapter boundaries."""

import pytest

from matcher.application_package import prepare_application_package
from matcher.ats_adapters import (
    GreenhouseAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
    UnsupportedATSUrlError,
    WorkdayAdapter,
    adapter_for_platform,
)


def package(url):
    return prepare_application_package(
        job_title="Software Engineer",
        company="Example Co",
        apply_url=url,
        resume_path="resume.pdf",
    )


@pytest.mark.parametrize(
    ("adapter", "url"),
    [
        (GreenhouseAdapter, "https://boards.greenhouse.io/example/jobs/123"),
        (LeverAdapter, "https://jobs.lever.co/example/123"),
        (WorkdayAdapter, "https://example.myworkdayjobs.com/en-US/Careers/job/123"),
        (SmartRecruitersAdapter, "https://jobs.smartrecruiters.com/Example/123"),
    ],
)
def test_supported_adapters_forward_only_valid_ats_urls(adapter, url):
    calls = []
    instance = adapter(lambda application: calls.append(application) or "accepted")
    result = instance.submit(package(url))
    assert result == "accepted"
    assert calls[0].apply_url == url


@pytest.mark.parametrize(
    "adapter",
    [GreenhouseAdapter, LeverAdapter, WorkdayAdapter, SmartRecruitersAdapter],
)
def test_adapters_reject_wrong_platform(adapter):
    instance = adapter(lambda application: "must not be called")
    with pytest.raises(UnsupportedATSUrlError):
        instance.submit(package("https://example.com/apply"))


def test_adapters_require_https():
    instance = GreenhouseAdapter(lambda application: "must not be called")
    with pytest.raises(UnsupportedATSUrlError, match="HTTPS"):
        instance.submit(package("http://boards.greenhouse.io/example/jobs/123"))


def test_platform_factory_supports_known_ats():
    adapter = adapter_for_platform("greenhouse", lambda application: "accepted")
    assert isinstance(adapter, GreenhouseAdapter)


def test_platform_factory_rejects_unknown_ats():
    with pytest.raises(ValueError, match="Unsupported ATS platform"):
        adapter_for_platform("unknown", lambda application: "must not be called")
