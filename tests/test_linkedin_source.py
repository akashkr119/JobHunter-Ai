from unittest.mock import MagicMock

import pytest

from crawler.linkedin_source import LinkedInSource


def test_linkedin_requires_authorized_client():
    with pytest.raises(ValueError, match="authorized integration client"):
        LinkedInSource().search("python")


def test_linkedin_normalizes_authorized_client_results():
    client = MagicMock()
    client.search_jobs.return_value = [
        {
            "title": "QA Automation Engineer",
            "company": "Example Automotive",
            "location": "Bengaluru",
            "url": "https://www.linkedin.com/jobs/view/123",
            "description": "Python pytest automotive testing",
        }
    ]

    source = LinkedInSource(client)
    jobs = source.search("QA Automation", location="Bengaluru")

    assert len(jobs) == 1
    assert jobs[0].title == "QA Automation Engineer"
    assert jobs[0].company == "Example Automotive"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].apply_url == "https://www.linkedin.com/jobs/view/123"
    assert jobs[0].platform == "linkedin"
    client.search_jobs.assert_called_once_with(query="QA Automation", location="Bengaluru")


def test_linkedin_skips_malformed_records():
    records = [
        {"title": "Valid", "company": "Example", "url": "https://example.com/job"},
        None,
        {"title": "Missing URL", "company": "Example"},
    ]

    jobs = LinkedInSource._normalize(records)

    assert len(jobs) == 1
    assert jobs[0].title == "Valid"
