from crawler.discovery import JobDiscovery, canonical_url
from crawler.job_scraper import Job
from crawler.source_manager import CallableJobSource, JobSourceManager


def make_job(url, platform):
    return Job("QA Engineer", "Acme", "Remote", url, platform=platform)


def test_canonical_url_removes_tracking_and_trailing_slash():
    assert canonical_url("HTTPS://Jobs.Example/123/?utm_source=indeed&gclid=abc") == "https://jobs.example/123/"


def test_duplicate_job_preserves_all_sources():
    one = CallableJobSource("adzuna", lambda **_: [make_job("https://jobs.example/123?utm_source=adzuna", "adzuna")])
    two = CallableJobSource("indeed", lambda **_: [make_job("https://JOBS.EXAMPLE/123/?utm_source=indeed", "indeed")])
    result = JobDiscovery(JobSourceManager([one, two])).discover()
    assert result.job_count == 1
    assert result.provenance[0].sources == ("adzuna", "indeed")
    assert result.provenance[0].canonical_url == "https://jobs.example/123/"


def test_distinct_query_parameters_remain_distinct():
    one = CallableJobSource("adzuna", lambda **_: [make_job("https://jobs.example/123?department=qa", "adzuna")])
    two = CallableJobSource("indeed", lambda **_: [make_job("https://jobs.example/123?department=dev", "indeed")])
    result = JobDiscovery(JobSourceManager([one, two])).discover()
    assert result.job_count == 2
