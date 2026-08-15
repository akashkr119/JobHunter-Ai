from crawler.job_scraper import Job
from crawler.source_manager import JobSourceManager


class FakeSource:
    def __init__(self, name, jobs=(), error=None):
        self.name = name
        self.jobs = jobs
        self.error = error

    def search(self, query="", **kwargs):
        if self.error:
            raise self.error
        return self.jobs


def make_job(url, title="QA Engineer"):
    return Job(
        title=title,
        company="Example",
        location="Bengaluru",
        description="QA testing",
        apply_url=url,
        platform="linkedin",
    )


def test_builtin_sources_can_register_linkedin():
    linkedin = FakeSource("LinkedIn")
    manager = JobSourceManager.with_builtin_sources(linkedin=linkedin)

    assert manager.names() == ("linkedin",)
    assert manager.get("LINKEDIN") is linkedin


def test_linkedin_participates_in_search_and_deduplication():
    linkedin = FakeSource("linkedin", [make_job("https://example.com/job/1")])
    other = FakeSource("other", [make_job("https://example.com/job/1", "Duplicate")])
    manager = JobSourceManager.with_builtin_sources(linkedin=linkedin)
    manager.register(other)

    jobs = manager.search("qa")

    assert len(jobs) == 1
    assert jobs[0].title == "QA Engineer"


def test_linkedin_failure_isolated_from_other_sources():
    linkedin = FakeSource("linkedin", error=RuntimeError("provider unavailable"))
    other = FakeSource("other", [make_job("https://example.com/job/2")])
    manager = JobSourceManager.with_builtin_sources(linkedin=linkedin)
    manager.register(other)

    results = manager.search_with_results("qa")

    assert results[0].source == "linkedin"
    assert results[0].jobs == ()
    assert "provider unavailable" in results[0].error
    assert results[1].jobs[0].apply_url == "https://example.com/job/2"
