import time

from crawler.job_scraper import Job
from crawler.source_manager import JobSourceManager


class FakeSource:
    def __init__(self, name, *, delay=0, jobs=None):
        self.name = name
        self.delay = delay
        self.jobs = jobs or []

    def search(self, query="", **kwargs):
        if self.delay:
            time.sleep(self.delay)
        return self.jobs


def make_job(url):
    return Job(title="QA Automation Engineer", company="Example", location="Bengaluru", apply_url=url)


def test_sources_run_concurrently():
    sources = [
        FakeSource("linkedin", delay=0.12, jobs=[make_job("https://example.com/linkedin")]),
        FakeSource("indeed", delay=0.12, jobs=[make_job("https://example.com/indeed")]),
        FakeSource("naukri", delay=0.12, jobs=[make_job("https://example.com/naukri")]),
    ]
    manager = JobSourceManager(sources, source_timeout_seconds=1, max_workers=3)

    started = time.monotonic()
    results = manager.search_with_results("QA Automation Engineer", location="Bengaluru")
    elapsed = time.monotonic() - started

    assert elapsed < 0.30
    assert [len(result.jobs) for result in results] == [1, 1, 1]
    assert all(result.error is None for result in results)


def test_slow_source_times_out_without_blocking_other_sources():
    sources = [
        FakeSource("linkedin", delay=0.01, jobs=[make_job("https://example.com/linkedin")]),
        FakeSource("naukri", delay=0.20, jobs=[make_job("https://example.com/naukri")]),
    ]
    manager = JobSourceManager(sources, source_timeout_seconds=0.05, max_workers=2)

    started = time.monotonic()
    results = manager.search_with_results("QA", location="Bengaluru")
    elapsed = time.monotonic() - started

    assert elapsed < 0.15
    assert results[0].jobs
    assert results[0].error is None
    assert results[1].jobs == ()
    assert results[1].error is not None
    assert "timeout" in results[1].error.lower()
