from types import ModuleType
import sys

from crawler.jobspy_source import JobSpySource


class FakeFrame:
    empty = False

    def to_dict(self, orient):
        assert orient == "records"
        return [
            {
                "site": "naukri",
                "title": "QA Automation Engineer",
                "company": "Example Mobility",
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India",
                "job_url": "https://www.naukri.com/job-1",
                "description": "Python Selenium API testing",
            }
        ]


def test_jobspy_source_normalizes_provider_records(monkeypatch):
    calls = {}
    module = ModuleType("jobspy")

    def scrape_jobs(**kwargs):
        calls.update(kwargs)
        return FakeFrame()

    module.scrape_jobs = scrape_jobs
    monkeypatch.setitem(sys.modules, "jobspy", module)

    jobs = list(
        JobSpySource("naukri").search(
            "QA Automation Engineer",
            location="Bengaluru",
            results_wanted=25,
            hours_old=72,
            country_indeed="India",
        )
    )

    assert len(jobs) == 1
    assert jobs[0].platform == "naukri"
    assert jobs[0].title == "QA Automation Engineer"
    assert jobs[0].location == "Bengaluru, Karnataka, India"
    assert calls["site_name"] == "naukri"
    assert calls["search_term"] == "QA Automation Engineer"
    assert calls["location"] == "Bengaluru"
    assert calls["results_wanted"] == 25
    assert calls["hours_old"] == 72
    assert calls["country_indeed"] == "India"


def test_jobspy_source_skips_invalid_records(monkeypatch):
    module = ModuleType("jobspy")

    class InvalidFrame:
        empty = False

        def to_dict(self, orient):
            return [
                {"title": "Missing company", "job_url": "https://example.com/1"},
                {"company": "Missing title", "job_url": "https://example.com/2"},
            ]

    module.scrape_jobs = lambda **_: InvalidFrame()
    monkeypatch.setitem(sys.modules, "jobspy", module)

    assert list(JobSpySource("indeed").search("QA", location="Delhi")) == []
