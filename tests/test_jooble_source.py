from unittest.mock import MagicMock

import pytest

from crawler.jooble_source import JoobleSource
from crawler.job_source import JobSearchRequest


def test_jooble_search_normalizes_results():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "jobs": [
            {
                "title": "Python Engineer",
                "company": "Example Corp",
                "location": "Mumbai",
                "link": "https://example.com/jobs/1",
                "snippet": "Python, pytest and automation",
            }
        ]
    }
    session.post.return_value = response

    jobs = JoobleSource(api_key="secret", session=session).search(
        JobSearchRequest(keywords=("Python",), locations=("Mumbai",), limit=10)
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Python Engineer"
    assert jobs[0].company == "Example Corp"
    assert jobs[0].platform == "jooble"
    assert jobs[0].apply_url == "https://example.com/jobs/1"
    response.raise_for_status.assert_called_once()
    session.post.assert_called_once()
    payload = session.post.call_args.kwargs["json"]
    assert payload["keywords"] == "Python"
    assert payload["location"] == "Mumbai"


def test_jooble_requires_api_key():
    with pytest.raises(RuntimeError, match="JOBHUNTER_JOOBLE_API_KEY"):
        JoobleSource(api_key=None, session=MagicMock()).search(
            JobSearchRequest(keywords=("Python",))
        )


def test_jooble_requires_keywords():
    with pytest.raises(ValueError, match="at least one keyword"):
        JoobleSource(api_key="secret", session=MagicMock()).search(JobSearchRequest())


def test_jooble_skips_invalid_listings():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "jobs": [
            {"title": "", "company": "Example", "link": "https://example.com/1"},
            {
                "title": "Valid Job",
                "company": "Example",
                "location": "Delhi",
                "link": "https://example.com/2",
                "snippet": "Valid",
            },
        ]
    }
    session.post.return_value = response

    jobs = JoobleSource(api_key="secret", session=session).search(
        JobSearchRequest(keywords=("engineer",))
    )
    assert [job.title for job in jobs] == ["Valid Job"]
