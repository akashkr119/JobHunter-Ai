"""Integration tests for unified recommendation ranking and alerts."""
from crawler.job_scraper import Job
from database.db import Database
from dashboard.app import app
from matcher.skill_matcher import SkillMatcher
from scheduler.scheduler import Scheduler

class Factory:
    def __init__(self,jobs):self.jobs=jobs
    def scrape(self,career_url,company=""):return list(self.jobs)
class Notifier:
    def __init__(self):self.sent=[]
    @staticmethod
    def format_job_alert(job,match,priority=None,priority_score=None):return f"{job.title} {match['score']} {priority}"
    def send(self,channel,**kwargs):self.sent.append((channel,kwargs));return {"success":True}
def make_job(url,title,description="Python Selenium",location="Bengaluru"):
    return Job(title=title,company="Example",location=location,apply_url=url,description=description,platform="greenhouse")

def test_dashboard_jobs_are_sorted_by_recommendation(tmp_path,monkeypatch):
    path=tmp_path/"jobs.db";db=Database(path);db.save_job(make_job("https://example.com/low","Manual QA"),match={"score":45,"preference_score":40,"preference_match":True});db.save_job(make_job("https://example.com/high","QA Automation Engineer"),match={"score":95,"preference_score":100,"preference_match":True});db.close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));payload=app.test_client().get("/api/jobs").get_json();assert payload["jobs"][0]["title"]=="QA Automation Engineer";assert payload["jobs"][0]["recommendation_score"]>payload["jobs"][1]["recommendation_score"];assert payload["jobs"][0]["recommendation_label"] in {"top_pick","strong_match"};assert "weighted" in payload["jobs"][0]["recommendation_breakdown"]

def test_job_detail_exposes_recommendation(tmp_path,monkeypatch):
    path=tmp_path/"jobs.db";db=Database(path);job_id=db.save_job(make_job("https://example.com/1","QA Automation Engineer"),match={"score":90,"preference_score":90,"preference_match":True});db.close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));job=app.test_client().get(f"/api/jobs/{job_id}").get_json();assert 0<=job["recommendation_score"]<=100;assert job["recommendation_label"] in {"top_pick","strong_match","good_match","consider"};assert job["recommendation_breakdown"]["weights"]["resume"]==0.5

def test_status_change_recalculates_recommendation(tmp_path,monkeypatch):
    path=tmp_path/"jobs.db";db=Database(path);job_id=db.save_job(make_job("https://example.com/1","QA Automation Engineer"),match={"score":90,"preference_score":90,"preference_match":True});db.close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();before=client.get(f"/api/jobs/{job_id}").get_json()["recommendation_score"];after=client.patch(f"/api/jobs/{job_id}/status",json={"status":"applied"}).get_json()["recommendation_score"];assert after<before

def test_smart_alert_can_require_recommendation_score(tmp_path):
    url="https://boards.greenhouse.io/example";n=Notifier();db=Database(tmp_path/"jobs.db");low=make_job("https://example.com/1","QA Automation Engineer",description="General quality assurance role");s=Scheduler(scraper_factory=Factory([low]),matcher=SkillMatcher(),database=db,notifier=n);summary=s.run_pipeline([url],["python","selenium"],notification={"channel":"telegram","minimum_priority":"low","minimum_recommendation_score":90});stored=db.list_jobs()[0];assert stored["match_score"]<100;assert summary["jobs_saved"]==1;assert summary["notifications_sent"]==0;assert summary["notifications_suppressed"]==1;assert n.sent==[];db.close()

def test_smart_alert_message_contains_recommendation(tmp_path):
    url="https://boards.greenhouse.io/example";n=Notifier();db=Database(tmp_path/"jobs.db");s=Scheduler(scraper_factory=Factory([make_job("https://example.com/1","QA Automation Engineer")]),matcher=SkillMatcher(),database=db,notifier=n);summary=s.run_pipeline([url],["python","selenium"],notification={"channel":"telegram","minimum_priority":"low","minimum_recommendation_score":0});assert summary["notifications_sent"]==1;assert "Recommendation:" in n.sent[0][1]["message"];db.close()

def test_invalid_recommendation_alert_threshold_is_reported(tmp_path):
    url="https://boards.greenhouse.io/example";n=Notifier();db=Database(tmp_path/"jobs.db");s=Scheduler(scraper_factory=Factory([make_job("https://example.com/1","QA Automation Engineer")]),matcher=SkillMatcher(),database=db,notifier=n);summary=s.run_pipeline([url],["python","selenium"],notification={"channel":"telegram","minimum_priority":"low","minimum_recommendation_score":101});assert summary["jobs_saved"]==1;assert summary["notifications_sent"]==0;assert summary["errors"][0]["stage"]=="notify";assert "minimum_recommendation_score" in summary["errors"][0]["error"];db.close()
