from crawler.job_scraper import Job
from crawler.job_source import JobSearchRequest
from crawler.source_pipeline import process_source_jobs
from matcher.job_preferences import JobPreferences


class FakeSourceManager:
    def names(self):
        return ("fake",)

    def search(self, request, sources=None):
        return [Job(
            title="Python Engineer",
            company="Example Co",
            location="Remote",
            apply_url="https://example.com/jobs/python",
            description="Python pytest automation",
            platform="fake",
        )]


class FakeMatcher:
    def match_job(self, skills, job):
        return {
            "score": 80.0,
            "matched_skills": ["python"],
            "missing_skills": [],
            "missing_required_skills": [],
        }


class FakeDatabase:
    def save_job(self, job, match=None):
        self.saved = (job, match)
        return 7

    def get_job(self, job_id):
        return {
            "id": job_id,
            "is_active": True,
            "application_status": "new",
            "priority_label": "high",
            "last_notified_priority": "",
            "match_score": 80.0,
            "preference_score": 100.0,
        }


class FakeScheduler:
    source_manager = FakeSourceManager()
    matcher = FakeMatcher()
    database = FakeDatabase()
    notifier = None

    def search_sources(self, request, sources=None):
        return self.source_manager.search(request, sources)

    def _existing_job(self, job):
        return None

    @staticmethod
    def _diagnose_skip(*args, **kwargs):
        return None


def test_source_jobs_use_existing_matching_and_persistence_pipeline():
    scheduler = FakeScheduler()
    result = process_source_jobs(
        scheduler,
        JobSearchRequest(keywords=("Python",), limit=10),
        ("python",),
        min_score=60,
        preferences=JobPreferences(),
    )

    assert result["jobs_found"] == 1
    assert result["jobs_saved"] == 1
    assert result["jobs_skipped"] == 0
    assert scheduler.database.saved[0].company == "Example Co"
    assert scheduler.database.saved[1]["score"] == 80.0
