"""Tests for the unified multi-source job discovery contract."""

import pytest

from crawler.job_scraper import Job
from crawler.job_source import JobSearchRequest, JobSource, JobSourceManager


class FakeSource(JobSource):
    name = "fake"

    def __init__(self, jobs=None, error=False):
        self.jobs = jobs or []
        self.error = error
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        if self.error:
            raise RuntimeError("source unavailable")
        return self.jobs


def make_job(title="QA Engineer"):
    return Job(
        title=title,
        company="Example",
        location="India",
        apply_url=f"https://example.com/{title.lower().replace(' ', '-')}",
        platform="fake",
    )


def test_search_request_has_normalized_defaults():
    request = JobSearchRequest()
    assert request.keywords == ()
    assert request.locations == ()
    assert request.remote is False
    assert request.limit == 50


def test_search_request_rejects_non_positive_limit():
    with pytest.raises(ValueError, match="greater than zero"):
        JobSearchRequest(limit=0)


def test_manager_registers_and_searches_source():
    source = FakeSource([make_job()])
    manager = JobSourceManager([source])
    request = JobSearchRequest(keywords=("qa",), locations=("India",))

    jobs = manager.search(request)

    assert manager.names() == ("fake",)
    assert jobs == source.jobs
    assert source.requests == [request]


def test_manager_rejects_duplicate_source_name():
    with pytest.raises(ValueError, match="already registered"):
        JobSourceManager([FakeSource(), FakeSource()])


def test_manager_rejects_non_source():
    with pytest.raises(TypeError, match="JobSource"):
        JobSourceManager([object()])


def test_manager_isolates_source_failure():
    failing = FakeSource(error=True)
    working = FakeSource([make_job("Automation Engineer")])
    working.name = "working"
    manager = JobSourceManager([failing, working])

    jobs = manager.search(JobSearchRequest())

    assert [job.title for job in jobs] == ["Automation Engineer"]


def test_manager_can_select_sources():
    first = FakeSource([make_job("First")])
    second = FakeSource([make_job("Second")])
    first.name = "first"
    second.name = "second"
    manager = JobSourceManager([first, second])

    jobs = manager.search(JobSearchRequest(), sources=["second"])

    assert [job.title for job in jobs] == ["Second"]


def test_unknown_source_is_rejected():
    manager = JobSourceManager()
    with pytest.raises(KeyError, match="Unknown job source"):
        manager.search(JobSearchRequest(), sources=["missing"])
