import pytest
from unittest.mock import MagicMock

from crawler.adzuna_source import AdzunaSource
from crawler.job_source import JobSearchRequest


def test_adzuna_requires_credentials():
    source = AdzunaSource(app_id=None, app_key=None)
    with pytest.raises(RuntimeError, match="Adzuna source requires"):
        source.search(JobSearchRequest(keywords=("python",)))


def test_adzuna_search_normalizes_results():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "results": [{
            "title": "Python Developer",
            "company": {"display_name": "Example Ltd"},
            "location": {"display_name": "Mumbai"},
            "redirect_url": "https://example.com/jobs/123",
            "description": "Python and API development",
        }]
    }
    session.get.return_value = response

    source = AdzunaSource(app_id="id", app_key="key", session=session)
    jobs = source.search(JobSearchRequest(keywords=("python",), locations=("Mumbai",), limit=10))

    assert len(jobs) == 1
    assert jobs[0].title == "Python Developer"
    assert jobs[0].company == "Example Ltd"
    assert jobs[0].location == "Mumbai"
    assert jobs[0].apply_url == "https://example.com/jobs/123"
    assert jobs[0].platform == "adzuna"
    response.raise_for_status.assert_called_once()
    session.get.assert_called_once()
    assert "what=python" in session.get.call_args.args[0]
    assert "where=Mumbai" in session.get.call_args.args[0]


def test_adzuna_skips_malformed_results():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "results": [{"title": ""}, {
            "title": "Valid Job",
            "company": {"display_name": "Example"},
            "redirect_url": "https://example.com/job",
        }]
    }
    session.get.return_value = response
    source = AdzunaSource(app_id="id", app_key="key", session=session)

    jobs = source.search(JobSearchRequest(keywords=("qa",)))

    assert [job.title for job in jobs] == ["Valid Job"]
