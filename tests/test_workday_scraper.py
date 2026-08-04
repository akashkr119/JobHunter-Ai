"""Tests for Workday scraper detail extraction."""

from unittest.mock import MagicMock, patch

import requests

from crawler.workday_scraper import WorkdayScraper


def test_build_detail_endpoint():
    endpoint = "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/jobs"
    path = "/job/Bengaluru/QA-Engineer_R123"
    assert WorkdayScraper.build_detail_endpoint(endpoint, path) == (
        "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/job/"
        "Bengaluru/QA-Engineer_R123"
    )


@patch("crawler.workday_scraper.requests.get")
def test_fetch_description_normalizes_detail_fields(mock_get):
    response = MagicMock()
    response.json.return_value = {
        "jobDescription": "<p>Python &amp; Selenium</p>",
        "qualifications": "<div>Pytest</div>",
        "additionalInformation": "Docker",
    }
    mock_get.return_value = response
    scraper = WorkdayScraper(timeout=7)

    description = scraper._fetch_description(
        "https://acme.example/wday/cxs/acme/Careers/jobs",
        "/job/India/QA_R1",
        {},
    )

    assert "Python & Selenium" in description
    assert "Pytest" in description
    assert "Docker" in description
    response.raise_for_status.assert_called_once()


@patch("crawler.workday_scraper.requests.get")
def test_fetch_description_falls_back_on_request_failure(mock_get):
    mock_get.side_effect = requests.RequestException("offline")
    scraper = WorkdayScraper()

    description = scraper._fetch_description(
        "https://acme.example/wday/cxs/acme/Careers/jobs",
        "/job/India/QA_R1",
        {"description": "<b>Fallback Python</b>"},
    )

    assert description == "Fallback Python"
