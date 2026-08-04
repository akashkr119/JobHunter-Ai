"""Unit tests for platform detector."""

import pytest

from crawler.platform_detector import PlatformDetector


def test_platform_detector_instance():
    detector = PlatformDetector()
    assert detector is not None


def test_has_detect_method():
    detector = PlatformDetector()
    assert hasattr(detector, "detect")


def test_detect_method_is_callable():
    detector = PlatformDetector()
    assert callable(detector.detect)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://boards.greenhouse.io/example", "greenhouse"),
        ("https://jobs.lever.co/example", "lever"),
        ("https://example.wd5.myworkdayjobs.com/en-US/Careers", "workday"),
        ("https://jobs.smartrecruiters.com/Example", "smartrecruiters"),
        ("https://example.oraclecloud.com/hcmUI/CandidateExperience", "oracle"),
        ("https://example.icims.com/jobs", "icims"),
        ("https://jobs.ashbyhq.com/example", "ashby"),
    ],
)
def test_detect_known_platforms(url, expected):
    detector = PlatformDetector()
    assert detector.detect(url) == expected


def test_detect_from_page_content():
    detector = PlatformDetector()
    html = '<a href="https://boards.greenhouse.io/example">Open roles</a>'
    assert detector.detect("https://example.com/careers", html) == "greenhouse"


def test_unknown_platform():
    detector = PlatformDetector()
    assert detector.detect("https://example.com/careers") == "unknown"


def test_empty_url_rejected():
    detector = PlatformDetector()
    with pytest.raises(ValueError):
        detector.detect("")
