"""Unit tests for scheduler and pipeline orchestration."""
import pytest
from crawler.job_scraper import Job
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from scheduler.scheduler import Scheduler
class FakeScraperFactory:
    def __init__(self,jobs_by_url=None,failing_urls=None):self.jobs_by_url=jobs_by_url or {};self.failing_urls=set(failing_urls or [])
    def scrape(self,career_url,company=""):
        if career_url in self.failing_urls:raise RuntimeError("scraper failed")
        return list(self.jobs_by_url.get(career_url,[]))
class FakeNotifier:
    def __init__(self,fail=False):self.fail=fail;self.sent=[]
    @staticmethod
    def format_job_alert(job,match):return f"{job.title}: {match['score']}%"
    def send(self,channel,**kwargs):
        if self.fail:raise RuntimeError("notification failed")
        self.sent.append((channel,kwargs));return {"success":True,"channel":channel}
def build_scheduler(tmp_path,factory=None,notifier=None):return Scheduler(scraper_factory=factory or FakeScraperFactory(),matcher=SkillMatcher(),database=Database(tmp_path/"jobs.db"),notifier=notifier)
def sample_job(url="https://example.com/jobs/1",description="Python Selenium Pytest Docker",platform="greenhouse",title="QA Automation Engineer",company="Example",location="Bengaluru"):return Job(title=title,company=company,location=location,apply_url=url,description=description,platform=platform)
def test_scheduler_instance(tmp_path):
    s=build_scheduler(tmp_path);assert s is not None;s.database.close()
def test_has_start_method(tmp_path):
    s=build_scheduler(tmp_path);assert callable(s.start);s.database.close()
def test_run_pipeline_scrapes_matches_and_saves_jobs(tmp_path):
    url="https://boards.greenhouse.io/example";s=build_scheduler(tmp_path,FakeScraperFactory({url:[sample_job()]}));summary=s.run_pipeline([url],["python","selenium","pytest"],min_score=50);assert summary=={"sources":1,"jobs_found":1,"jobs_saved":1,"jobs_skipped":0,"jobs_expired":0,"notifications_sent":0,"errors":[]};assert s.database.list_jobs()[0]["is_active"] is True;s.database.close()
def test_pipeline_persists_weighted_match_explanation(tmp_path):
    url="https://boards.greenhouse.io/example";job=sample_job(description="Requirements: Python and Selenium are required.\nNice to have: Docker.\nYou will use Pytest.");s=build_scheduler(tmp_path,FakeScraperFactory({url:[job]}));summary=s.run_pipeline([url],["python","selenium","pytest"],min_score=50);stored=s.database.list_jobs()[0];assert summary["jobs_saved"]==1;assert {"python","selenium"}.issubset(stored["required_skills"]);assert "docker" in stored["preferred_skills"];assert stored["match_score"]>=80;s.database.close()
def test_run_pipeline_filters_jobs_below_minimum_score(tmp_path):
    url="https://jobs.lever.co/example";job=sample_job(url="https://example.com/jobs/2",description="Python Docker Kubernetes AWS",platform="lever");s=build_scheduler(tmp_path,FakeScraperFactory({url:[job]}));summary=s.run_pipeline([url],["python"],min_score=50);assert summary["jobs_skipped"]==1;assert s.database.list_jobs()==[];s.database.close()
def test_successful_scrape_marks_disappeared_jobs_inactive(tmp_path):
    url="https://boards.greenhouse.io/example";old=sample_job(url="https://example.com/jobs/old",title="QA Automation Engineer");keep=sample_job(url="https://example.com/jobs/keep",title="Senior QA Automation Engineer");factory=FakeScraperFactory({url:[old,keep]});s=build_scheduler(tmp_path,factory);s.run_pipeline([url],["python","selenium","pytest"],min_score=0);factory.jobs_by_url[url]=[keep];summary=s.run_pipeline([url],["python","selenium","pytest"],min_score=0);assert summary["jobs_expired"]==1;assert s.database.list_jobs(active=False)[0]["apply_url"]==old.apply_url;assert s.database.list_jobs(active=True)[0]["apply_url"]==keep.apply_url;s.database.close()
def test_failed_scrape_never_expires_existing_jobs(tmp_path):
    url="https://boards.greenhouse.io/example";factory=FakeScraperFactory({url:[sample_job()]});s=build_scheduler(tmp_path,factory);s.run_pipeline([url],["python"],min_score=0);factory.failing_urls.add(url);summary=s.run_pipeline([url],["python"],min_score=0);assert summary["jobs_expired"]==0;assert summary["errors"][0]["stage"]=="scrape";assert s.database.list_jobs()[0]["is_active"] is True;s.database.close()
def test_below_threshold_job_counts_as_seen_for_lifecycle(tmp_path):
    url="https://boards.greenhouse.io/example";job=sample_job(description="Python Docker Kubernetes AWS");factory=FakeScraperFactory({url:[job]});s=build_scheduler(tmp_path,factory);s.database.save_job(job,match={"score":90});summary=s.run_pipeline([url],["python"],min_score=90);assert summary["jobs_skipped"]==1;assert summary["jobs_expired"]==0;assert s.database.get_job(1)["is_active"] is True;s.database.close()
def test_expiry_is_scoped_to_platform(tmp_path):
    gh="https://boards.greenhouse.io/example";s=build_scheduler(tmp_path,FakeScraperFactory({gh:[]}));s.database.save_job(sample_job(url="https://example.com/gh",platform="greenhouse",title="Greenhouse QA Engineer"));s.database.save_job(sample_job(url="https://example.com/lever",platform="lever",title="Lever QA Engineer"));summary=s.run_pipeline([gh],["python"],min_score=0);assert summary["jobs_expired"]==1;assert s.database.list_jobs(active=False)[0]["platform"]=="greenhouse";assert s.database.list_jobs(active=True)[0]["platform"]=="lever";s.database.close()
def test_reappearing_job_becomes_active_again(tmp_path):
    url="https://boards.greenhouse.io/example";job=sample_job();factory=FakeScraperFactory({url:[job]});s=build_scheduler(tmp_path,factory);s.run_pipeline([url],["python"],min_score=0);factory.jobs_by_url[url]=[];s.run_pipeline([url],["python"],min_score=0);assert s.database.list_jobs(active=False)[0]["is_active"] is False;factory.jobs_by_url[url]=[job];s.run_pipeline([url],["python"],min_score=0);assert s.database.list_jobs(active=True)[0]["apply_url"]==job.apply_url;s.database.close()
def test_matching_job_sends_notification(tmp_path):
    url="https://boards.greenhouse.io/example";n=FakeNotifier();s=build_scheduler(tmp_path,FakeScraperFactory({url:[sample_job()]}),n);summary=s.run_pipeline([url],["python","selenium","pytest"],min_score=50,notification={"channel":"telegram","chat_id":"123"});assert summary["notifications_sent"]==1;assert len(n.sent)==1;s.database.close()
def test_notification_failure_does_not_lose_saved_job(tmp_path):
    url="https://boards.greenhouse.io/example";s=build_scheduler(tmp_path,FakeScraperFactory({url:[sample_job()]}),FakeNotifier(True));summary=s.run_pipeline([url],["python","selenium","pytest"],min_score=50,notification={"channel":"telegram"});assert summary["jobs_saved"]==1;assert summary["errors"][0]["stage"]=="notify";s.database.close()
def test_one_failed_source_does_not_stop_other_sources(tmp_path):
    bad="https://example.com/bad";good="https://boards.greenhouse.io/good";s=build_scheduler(tmp_path,FakeScraperFactory({good:[sample_job()]},{bad}));summary=s.run_pipeline([bad,good],["python"],min_score=0);assert summary["sources"]==2;assert summary["jobs_saved"]==1;assert summary["errors"][0]["stage"]=="scrape";s.database.close()
def test_invalid_minimum_score_rejected(tmp_path):
    s=build_scheduler(tmp_path)
    with pytest.raises(ValueError,match="min_score"):s.run_pipeline([],[],101)
    s.database.close()
def test_add_job_rejects_non_positive_interval(tmp_path):
    s=build_scheduler(tmp_path)
    with pytest.raises(ValueError,match="hours"):s.add_job(lambda:None,hours=0)
    s.database.close()
def test_add_pipeline_job_registers_interval_job(tmp_path):
    s=build_scheduler(tmp_path);job=s.add_pipeline_job(["https://boards.greenhouse.io/example"],["python"],hours=2,min_score=60);assert job.func==s.run_pipeline;s.database.close()
