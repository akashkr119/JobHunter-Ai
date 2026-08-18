from crawler.indeed_source import IndeedSource
from crawler.source_manager import JobSourceManager


class StubIndeedClient:
    def search_jobs(self, query="", **kwargs):
        return [
            {
                "title": "Python Engineer",
                "company": "Example Ltd",
                "location": "Pune",
                "url": "https://example.com/jobs/42",
            }
        ]


def test_builtin_sources_can_register_indeed():
    source = IndeedSource(StubIndeedClient())
    manager = JobSourceManager.with_builtin_sources(indeed=source)

    assert manager.names() == ("indeed",)
    jobs = manager.search("python", sources=("INDEED",), location="Pune")
    assert len(jobs) == 1
    assert jobs[0].platform == "indeed"


def test_indeed_failure_isolated_from_other_sources():
    class BrokenIndeed:
        name = "indeed"

        def search(self, query="", **kwargs):
            raise RuntimeError("Indeed unavailable")

    class HealthySource:
        name = "other"

        def search(self, query="", **kwargs):
            return [IndeedSource._normalize([
                {"title": "Healthy", "company": "Example", "url": "https://example.com/healthy"}
            ])[0]]

    manager = JobSourceManager([BrokenIndeed(), HealthySource()])
    results = manager.search_with_results("python")

    assert results[0].source == "indeed"
    assert results[0].error and "Indeed unavailable" in results[0].error
    assert results[1].error is None
    assert len(results[1].jobs) == 1
