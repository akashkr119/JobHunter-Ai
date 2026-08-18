from crawler.naukri_source import NaukriSource
from crawler.source_manager import JobSourceManager


class StubNaukriClient:
    def search_jobs(self, query="", **kwargs):
        return [
            {
                "title": "Python Engineer",
                "company": "Example Ltd",
                "location": "Pune",
                "url": "https://example.com/jobs/naukri-42",
            }
        ]


def test_builtin_sources_can_register_naukri():
    source = NaukriSource(StubNaukriClient())
    manager = JobSourceManager.with_builtin_sources(naukri=source)

    assert manager.names() == ("naukri",)
    jobs = manager.search("python", sources=("NAUKRI",), location="Pune")
    assert len(jobs) == 1
    assert jobs[0].platform == "naukri"


def test_naukri_failure_isolated_from_other_sources():
    class BrokenNaukri:
        name = "naukri"

        def search(self, query="", **kwargs):
            raise RuntimeError("Naukri unavailable")

    class HealthySource:
        name = "other"

        def search(self, query="", **kwargs):
            return NaukriSource._normalize([
                {"title": "Healthy", "company": "Example", "url": "https://example.com/healthy"}
            ])

    manager = JobSourceManager([BrokenNaukri(), HealthySource()])
    results = manager.search_with_results("python")

    assert results[0].source == "naukri"
    assert results[0].error and "Naukri unavailable" in results[0].error
    assert results[1].error is None
    assert len(results[1].jobs) == 1
