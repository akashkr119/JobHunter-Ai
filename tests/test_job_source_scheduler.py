from crawler.job_source import JobSearchRequest, JobSource
from crawler.job_scraper import Job
from scheduler.scheduler import Scheduler


class StubSource(JobSource):
    name = "stub"

    def search(self, request):
        return [
            Job(
                title="QA Automation Engineer",
                company="Example Corp",
                location="Remote",
                description="Python Selenium pytest",
                apply_url="https://example.com/jobs/1",
                platform="stub",
            )
        ]


def test_scheduler_exposes_configured_source_manager():
    scheduler = Scheduler(source_manager=None)
    try:
        scheduler.source_manager.register(StubSource())
        jobs = scheduler.search_sources(JobSearchRequest(keywords=("QA",)))
        assert len(jobs) == 1
        assert jobs[0].title == "QA Automation Engineer"
    finally:
        scheduler.database.close()


def test_scheduler_can_select_registered_sources():
    scheduler = Scheduler()
    try:
        scheduler.source_manager.register(StubSource())
        jobs = scheduler.search_sources(JobSearchRequest(keywords=("QA",)), sources=("stub",))
        assert [job.company for job in jobs] == ["Example Corp"]
    finally:
        scheduler.database.close()
