from unittest.mock import MagicMock

import pytest

from crawler.naukri_source import NaukriSource


def test_naukri_requires_authorized_client():
    with pytest.raises(ValueError, match="authorized integration client"):
        NaukriSource().search("python")


def test_naukri_normalizes_authorized_client_results():
    client = MagicMock()
    client.search_jobs.return_value = [
        {
            "title": "QA Automation Engineer",
            "company": "Example Automotive",
            "location": "Bengaluru",
            "url": "https://example.com/jobs/123",
            "description": "Python pytest automotive testing",
        }
    ]

    jobs = NaukriSource(client).search("QA Automation", location="Bengaluru")

    assert len(jobs) == 1
    assert jobs[0].title == "QA Automation Engineer"
    assert jobs[0].company == "Example Automotive"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].apply_url == "https://example.com/jobs/123"
    assert jobs[0].platform == "naukri"
    client.search_jobs.assert_called_once_with(query="QA Automation", location="Bengaluru")


def test_naukri_skips_malformed_records():
    records = [
        {"title": "Valid", "company": "Example", "url": "https://example.com/job"},
        None,
        {"title": "Missing URL", "company": "Example"},
    ]

    jobs = NaukriSource._normalize(records)

    assert len(jobs) == 1
    assert jobs[0].title == "Valid"
