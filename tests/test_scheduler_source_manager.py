import pytest

from crawler.job_scraper import Job
from crawler.job_source import JobSearchRequest, JobSource
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from scheduler.scheduler import Scheduler


class FakeSource(JobSource):
    name = "fake"

    def __init__(self, jobs=None):
        self.jobs = jobs or []
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        return list(self.jobs)


def test_scheduler_exposes_registered_source_manager(tmp_path):
    job = Job(
        title="QA Engineer",
        company="Example",
        location="Bengaluru",
        apply_url="https://example.com/jobs/1",
    )
    source = FakeSource([job])
    scheduler = Scheduler(
        matcher=SkillMatcher(),
        database=Database(tmp_path / "jobs.db"),
        source_manager=None,
    )
    scheduler.source_manager.register(source)

    request = JobSearchRequest(keywords=("qa",), locations=("Bengaluru",))
    results = scheduler.search_sources(request, sources=["fake"])

    assert results == [job]
    assert source.requests == [request]
    scheduler.database.close()


def test_scheduler_can_select_multiple_sources(tmp_path):
    first = FakeSource([Job("QA", "A", "Bengaluru", "https://a.example/1")])
    second = FakeSource([Job("SDET", "B", "Pune", "https://b.example/1")])
    first.name = "first"
    second.name = "second"
    scheduler = Scheduler(database=Database(tmp_path / "jobs.db"))
    scheduler.source_manager.register(first)
    scheduler.source_manager.register(second)

    results = scheduler.search_sources(JobSearchRequest(keywords=("test",)), sources=["first", "second"])

    assert [job.company for job in results] == ["A", "B"]
    scheduler.database.close()


def test_scheduler_source_failure_does_not_break_other_sources(tmp_path):
    class BrokenSource(JobSource):
        name = "broken"

        def search(self, request):
            raise RuntimeError("source unavailable")

    good = FakeSource([Job("QA", "Good", "Remote", "https://good.example/1")])
    scheduler = Scheduler(database=Database(tmp_path / "jobs.db"))
    scheduler.source_manager.register(BrokenSource())
    scheduler.source_manager.register(good)

    results = scheduler.search_sources(JobSearchRequest(), sources=["broken", "fake"])

    assert results == good.jobs
    scheduler.database.close()


def test_scheduler_unknown_source_is_reported(tmp_path):
    scheduler = Scheduler(database=Database(tmp_path / "jobs.db"))
    with pytest.raises(KeyError, match="Unknown job source"):
        scheduler.search_sources(JobSearchRequest(), sources=["missing"])
    scheduler.database.close()
