"""Tests for SmartRecruiters scraper detail extraction."""

from unittest.mock import MagicMock, patch

import requests

from crawler.smartrecruiters_scraper import SmartRecruitersScraper


@patch("crawler.smartrecruiters_scraper.requests.get")
def test_fetch_description_combines_job_ad_sections(mock_get):
    response = MagicMock()
    response.json.return_value = {
        "jobAd": {
            "sections": {
                "jobDescription": "<p>Python automation</p>",
                "qualifications": "<p>Selenium &amp; Pytest</p>",
            }
        }
    }
    mock_get.return_value = response
    scraper = SmartRecruitersScraper(timeout=9)

    description = scraper._fetch_description("Example", {"id": "123"})

    assert "Python automation" in description
    assert "Selenium & Pytest" in description
    response.raise_for_status.assert_called_once()


@patch("crawler.smartrecruiters_scraper.requests.get")
def test_fetch_description_falls_back_on_request_failure(mock_get):
    mock_get.side_effect = requests.RequestException("offline")
    scraper = SmartRecruitersScraper()

    description = scraper._fetch_description(
        "Example",
        {"id": "123", "description": "<b>Fallback Java</b>"},
    )

    assert description == "Fallback Java"


def test_fetch_description_uses_listing_when_id_missing():
    scraper = SmartRecruitersScraper()
    description = scraper._fetch_description(
        "Example",
        {"jobAd": "<p>Embedded Python role</p>"},
    )
    assert description == "Embedded Python role"
