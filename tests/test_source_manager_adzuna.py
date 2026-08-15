from unittest.mock import MagicMock

from crawler.source_manager import JobSourceManager


def _job(url: str):
    job = MagicMock()
    job.apply_url = url
    return job


def test_builtin_manager_registers_configured_adzuna_source():
    adzuna = MagicMock()
    adzuna.name = "Adzuna"
    adzuna.search.return_value = [_job("https://example.com/1")]

    manager = JobSourceManager.with_builtin_sources(adzuna=adzuna)

    assert manager.names() == ("adzuna",)
    assert manager.get("ADZUNA") is adzuna


def test_manager_search_deduplicates_jobs_across_sources():
    first = MagicMock()
    first.name = "first"
    first.search.return_value = [_job("https://example.com/job/1")]

    adzuna = MagicMock()
    adzuna.name = "adzuna"
    adzuna.search.return_value = [
        _job("https://example.com/job/1/"),
        _job("https://example.com/job/2"),
    ]

    manager = JobSourceManager([first, adzuna])
    jobs = manager.search("python")

    assert [job.apply_url for job in jobs] == [
        "https://example.com/job/1",
        "https://example.com/job/2",
    ]
    first.search.assert_called_once_with("python")
    adzuna.search.assert_called_once_with("python")


def test_adzuna_failure_does_not_block_other_sources():
    good = MagicMock()
    good.name = "good"
    good.search.return_value = [_job("https://example.com/good")]

    adzuna = MagicMock()
    adzuna.name = "adzuna"
    adzuna.search.side_effect = RuntimeError("API unavailable")

    manager = JobSourceManager([good, adzuna])
    results = manager.search_with_results("python")

    assert results[0].jobs[0].apply_url == "https://example.com/good"
    assert results[0].error is None
    assert results[1].jobs == ()
    assert "API unavailable" in results[1].error
