from unittest.mock import MagicMock

import pytest

from crawler.adzuna_source import AdzunaSource


def test_adzuna_requires_credentials():
    with pytest.raises(ValueError, match="JOBHUNTER_ADZUNA_APP_ID"):
        AdzunaSource(app_id=None, app_key=None).search("python")


def test_adzuna_search_uses_credentials_and_normalizes_jobs():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "results": [
            {
                "title": "Python Engineer",
                "company": {"display_name": "Example Ltd"},
                "location": {"display_name": "Bengaluru"},
                "redirect_url": "https://example.com/jobs/1",
                "description": "Python backend role",
            }
        ]
    }
    session.get.return_value = response

    source = AdzunaSource(app_id="id", app_key="key", session=session, timeout=9)
    jobs = list(source.search("python", location="Bengaluru", results_per_page=10))

    assert len(jobs) == 1
    assert jobs[0].title == "Python Engineer"
    assert jobs[0].company == "Example Ltd"
    assert jobs[0].apply_url == "https://example.com/jobs/1"
    session.get.assert_called_once_with(
        "https://api.adzuna.com/v1/api/jobs/in/search/1",
        params={
            "app_id": "id",
            "app_key": "key",
            "results_per_page": 10,
            "what": "python",
            "where": "Bengaluru",
        },
        timeout=9,
    )
    response.raise_for_status.assert_called_once_with()


def test_adzuna_skips_malformed_records():
    results = AdzunaSource._normalize([
        {"title": "Good", "company": {"display_name": "Example Ltd"}, "location": {}, "redirect_url": "https://example.com/good"},
        None,
    ])
    assert len(results) == 1
    assert results[0].title == "Good"
