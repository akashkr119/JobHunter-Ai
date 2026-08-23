from crawler.source_manager import JobSourceManager
from scheduler.source_schedule import run_source_cycle


class Source:
    name = "test"

    def search(self, query="", **kwargs):
        return []


def test_run_source_cycle_returns_isolated_results():
    manager = JobSourceManager([Source()])
    results = run_source_cycle(manager, query="python")
    assert len(results) == 1
    assert results[0].source == "test"
    assert results[0].error is None
