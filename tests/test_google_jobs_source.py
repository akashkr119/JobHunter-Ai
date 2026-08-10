from unittest.mock import MagicMock

import pytest

from crawler.google_jobs_source import GoogleJobsSource
from crawler.job_source import JobSearchRequest


def test_google_jobs_source_requires_api_key():
    source = GoogleJobsSource(api_key="", session=MagicMock())
    with pytest.raises(ValueError, match="SerpApi API key"):
        source.search(JobSearchRequest(keywords=("python",)))


def test_google_jobs_source_search_normalizes_results():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "jobs_results": [
            {
                "title": "QA Automation Engineer",
                "company_name": "Example Motors",
                "location": "Pune, Maharashtra",
                "description": "Python Selenium API testing",
                "share_link": "https://example.com/jobs/qa",
            }
        ]
    }
    session.get.return_value = response

    source = GoogleJobsSource(api_key="test-key", session=session, timeout=9)
    jobs = source.search(
        JobSearchRequest(keywords=("QA Automation",), locations=("Pune",), limit=10)
    )

    assert len(jobs) == 1
    assert jobs[0].title == "QA Automation Engineer"
    assert jobs[0].company == "Example Motors"
    assert jobs[0].platform == "google_jobs"
    assert jobs[0].apply_url == "https://example.com/jobs/qa"
    session.get.assert_called_once()
    assert session.get.call_args.kwargs["timeout"] == 9
    assert session.get.call_args.kwargs["params"]["engine"] == "google_jobs"
    assert session.get.call_args.kwargs["params"]["q"] == "QA Automation"
    response.raise_for_status.assert_called_once()


def test_google_jobs_source_uses_apply_option_when_share_link_missing():
    item = {
        "title": "Python Engineer",
        "company_name": "Example",
        "location": "Remote",
        "description": "Python",
        "apply_options": [{"title": "Apply on Indeed", "link": "https://indeed.com/viewjob?id=1"}],
    }

    job = GoogleJobsSource._parse_job(item)

    assert job is not None
    assert job.apply_url == "https://indeed.com/viewjob?id=1"


def test_google_jobs_source_skips_incomplete_results():
    assert GoogleJobsSource._parse_job({"title": "Missing company"}) is None


def test_google_jobs_source_reports_api_errors():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {"error": "invalid api key"}
    session.get.return_value = response

    source = GoogleJobsSource(api_key="bad", session=session)
    with pytest.raises(RuntimeError, match="invalid api key"):
        source.search(JobSearchRequest(keywords=("tester",)))
