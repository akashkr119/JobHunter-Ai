from unittest.mock import MagicMock

import pytest

from crawler.indeed_source import IndeedSource


def test_indeed_requires_authorized_client():
    with pytest.raises(ValueError, match="authorized integration client"):
        IndeedSource().search("python")


def test_indeed_normalizes_authorized_client_results():
    client = MagicMock()
    client.search_jobs.return_value = [
        {
            "title": "Python Engineer",
            "company": "Example Ltd",
            "location": "Pune",
            "url": "https://example.com/jobs/42",
            "description": "Python backend role",
        }
    ]

    source = IndeedSource(client)
    jobs = source.search("Python", location="Pune")

    assert len(jobs) == 1
    assert jobs[0].title == "Python Engineer"
    assert jobs[0].company == "Example Ltd"
    assert jobs[0].location == "Pune"
    assert jobs[0].apply_url == "https://example.com/jobs/42"
    assert jobs[0].platform == "indeed"
    client.search_jobs.assert_called_once_with(query="Python", location="Pune")


def test_indeed_skips_malformed_records():
    records = [
        {"title": "Valid", "company": "Example", "url": "https://example.com/job"},
        None,
        {"title": "Missing URL", "company": "Example"},
    ]

    jobs = IndeedSource._normalize(records)

    assert len(jobs) == 1
    assert jobs[0].title == "Valid"
