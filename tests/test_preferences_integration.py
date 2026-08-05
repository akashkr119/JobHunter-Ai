"""Integration tests for target-profile preferences."""
from crawler.job_scraper import Job
from database.db import Database
from matcher.job_preferences import JobPreferences
from matcher.skill_matcher import SkillMatcher
from scheduler.scheduler import Scheduler

class Factory:
    def __init__(self,jobs):self.jobs=jobs
    def scrape(self,career_url,company=""):return list(self.jobs)

def job(url="https://example.com/1",description="Python Selenium hybrid role"):
    return Job(title="QA Automation Engineer",company="Example",location="Bengaluru",apply_url=url,description=description,platform="greenhouse")

def test_database_persists_preference_result_after_reopen(tmp_path):
    path=tmp_path/"jobs.db";db=Database(path);details={"preference_score":100.0,"preference_match":True,"matched_titles":["qa automation engineer"],"matched_locations":["bengaluru"],"matched_work_modes":["hybrid"],"matched_keywords":["python"],"excluded_keywords":[]};job_id=db.save_job(job(),match={"score":90,"preference_score":100,"preference_match":True,"preference_details":details});db.close();db=Database(path);stored=db.get_job(job_id);assert stored["preference_score"]==100.0;assert stored["preference_match"] is True;assert stored["preference_details"]["matched_work_modes"]==["hybrid"];db.close()

def test_pipeline_persists_target_profile_evaluation(tmp_path):
    db=Database(tmp_path/"jobs.db");s=Scheduler(scraper_factory=Factory([job()]),matcher=SkillMatcher(),database=db);prefs=JobPreferences(target_titles=("qa automation engineer",),preferred_locations=("bengaluru",),work_modes=("hybrid",),desired_keywords=("python",));summary=s.run_pipeline(["https://boards.greenhouse.io/example"],["python","selenium"],preferences=prefs);stored=db.list_jobs()[0];assert summary["jobs_saved"]==1;assert stored["preference_score"]==100.0;assert stored["preference_match"] is True;assert stored["preference_details"]["matched_titles"]==["qa automation engineer"];db.close()

def test_pipeline_excludes_blocked_keyword_without_saving(tmp_path):
    db=Database(tmp_path/"jobs.db");s=Scheduler(scraper_factory=Factory([job(description="Python Selenium contract position")]),matcher=SkillMatcher(),database=db);summary=s.run_pipeline(["https://boards.greenhouse.io/example"],["python"],preferences={"excluded_keywords":["contract"]});assert summary["jobs_found"]==1;assert summary["jobs_preference_excluded"]==1;assert summary["jobs_skipped"]==1;assert summary["jobs_saved"]==0;assert db.list_jobs()==[];db.close()

def test_preference_excluded_job_still_counts_seen_for_lifecycle(tmp_path):
    db=Database(tmp_path/"jobs.db");j=job(description="contract role");db.save_job(j,match={"score":80});s=Scheduler(scraper_factory=Factory([j]),matcher=SkillMatcher(),database=db);summary=s.run_pipeline(["https://boards.greenhouse.io/example"],["python"],preferences={"excluded_keywords":["contract"]});assert summary["jobs_expired"]==0;assert db.get_job(1)["is_active"] is True;db.close()
