from crawler.discovery import JobDiscovery
from crawler.job_scraper import Job
from crawler.source_manager import CallableJobSource, JobSourceManager


def job(url, platform="test"):
    return Job("Engineer", "Acme", "Remote", url, platform=platform)


def test_discovery_combines_sources_and_deduplicates():
    first = CallableJobSource("adzuna", lambda **_: [job("https://jobs.example/1", "adzuna"), job("https://jobs.example/2", "adzuna")])
    second = CallableJobSource("indeed", lambda **_: [job("https://jobs.example/2", "indeed"), job("https://jobs.example/3", "indeed")])
    result = JobDiscovery(JobSourceManager([first, second])).discover("qa")
    assert result.job_count == 3
    assert result.source_count == 2
    assert result.failed_sources == ()


def test_discovery_isolates_source_failure():
    good = CallableJobSource("adzuna", lambda **_: [job("https://jobs.example/good")])
    bad = CallableJobSource("indeed", lambda **_: (_ for _ in ()).throw(RuntimeError("boom")))
    result = JobDiscovery(JobSourceManager([good, bad])).discover()
    assert result.job_count == 1
    assert result.failed_sources == ("indeed",)


def test_discovery_can_select_sources():
    first = CallableJobSource("adzuna", lambda **_: [job("https://jobs.example/1")])
    second = CallableJobSource("naukri", lambda **_: [job("https://jobs.example/2")])
    result = JobDiscovery(JobSourceManager([first, second])).discover(sources=["naukri"])
    assert result.job_count == 1
    assert result.runs[0].source == "naukri"
