from crawler.source_manager import JobSourceManager
from crawler.source_health import SourceStatus


class Healthy:
    name = "healthy"

    def search(self, query="", **kwargs):
        return []


class Broken:
    name = "broken"

    def search(self, query="", **kwargs):
        raise RuntimeError("provider unavailable")


def test_manager_reports_health_for_each_source():
    manager = JobSourceManager([Healthy(), Broken()])

    health = manager.health()

    assert health[0].source == "healthy"
    assert health[0].status is SourceStatus.AVAILABLE
    assert health[1].source == "broken"
    assert health[1].status is SourceStatus.FAILED
    assert health[1].message == "RuntimeError: provider unavailable"
