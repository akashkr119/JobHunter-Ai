from crawler.job_scraper import Job
from crawler.source_manager import CallableJobSource, JobSourceManager


class FakeSource:
    def __init__(self, name="Fake", jobs=None, error=None):
        self.name = name
        self.jobs = jobs or []
        self.error = error

    def search(self, query="", **kwargs):
        if self.error:
            raise self.error
        return self.jobs


def make_job(url, title="Engineer"):
    return Job(title=title, company="Example", location="Remote", apply_url=url)


def test_manager_registers_and_lists_sources():
    manager = JobSourceManager([FakeSource()])
    assert manager.names() == ("fake",)
    assert manager.get("FAKE").name == "Fake"


def test_manager_rejects_invalid_source():
    class Invalid:
        name = "invalid"

    manager = JobSourceManager()
    try:
        manager.register(Invalid())
    except ValueError as exc:
        assert "search()" in str(exc)
    else:
        raise AssertionError("invalid source was accepted")


def test_manager_isolates_source_failure():
    good = FakeSource(name="good", jobs=[make_job("https://example.com/1")])
    bad = FakeSource(name="bad", error=RuntimeError("provider unavailable"))
    manager = JobSourceManager([good, bad])

    results = manager.search_with_results("python")
    assert results[0].source == "good"
    assert len(results[0].jobs) == 1
    assert results[0].error is None
    assert results[1].source == "bad"
    assert results[1].error is not None


def test_manager_deduplicates_by_apply_url():
    first = make_job("https://example.com/job/1", "First")
    duplicate = make_job("https://example.com/job/1/", "Duplicate")
    second = make_job("https://example.com/job/2", "Second")

    unique = JobSourceManager.deduplicate([first, duplicate, second])
    assert [job.title for job in unique] == ["First", "Second"]


def test_callable_source_adapter():
    source = CallableJobSource(
        "api",
        lambda query="", **kwargs: [make_job("https://example.com/api")],
    )
    manager = JobSourceManager([source])
    jobs = manager.search("python")
    assert len(jobs) == 1
    assert jobs[0].platform == "unknown"


def test_unknown_source_has_actionable_error():
    manager = JobSourceManager()
    try:
        manager.get("linkedin")
    except ValueError as exc:
        assert "Unknown job source" in str(exc)
    else:
        raise AssertionError("unknown source was accepted")
