from unittest.mock import MagicMock

from crawler.indeed_source import IndeedSource
from crawler.source_manager import JobSourceManager


def test_builtin_manager_registers_indeed():
    client = MagicMock()
    source = IndeedSource(client)

    manager = JobSourceManager.with_builtin_sources(indeed=source)

    assert manager.get("INDEED") is source
    assert "indeed" in manager.names()


def test_indeed_failure_isolated_from_other_sources():
    good = MagicMock()
    good.name = "good"
    good.search.return_value = []

    bad = IndeedSource(MagicMock())
    bad.client.search_jobs.side_effect = RuntimeError("provider unavailable")

    manager = JobSourceManager([good, bad])
    results = manager.search_with_results("python")

    assert results[0].source == "good"
    assert results[0].error is None
    assert results[1].source == "indeed"
    assert results[1].jobs == ()
    assert "provider unavailable" in results[1].error
