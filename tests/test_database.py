"""Unit tests for database layer."""
import sqlite3
from datetime import datetime,timedelta,timezone
import pytest
from crawler.job_scraper import Job
from database.db import Database

def make_job(db,title,score=80,status="new",active=True,days_old=0):
    job_id=db.save_job({"title":title,"company":"Priority Co","location":"Remote","apply_url":f"https://example.com/{title.lower().replace(' ','-')}","platform":"greenhouse"},match={"score":score})
    seen=(datetime.now(timezone.utc)-timedelta(days=days_old)).strftime("%Y-%m-%d %H:%M:%S");db.execute("UPDATE jobs SET last_seen_at=?, discovered_at=? WHERE id=?",(seen,seen,job_id))
    if status!="new":db.update_application_status(job_id,status)
    if not active:db.execute("UPDATE jobs SET is_active=0 WHERE id=?",(job_id,))
    return job_id

def test_priority_score_is_exposed(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=make_job(db,"Excellent Match",95);job=db.get_job(job_id);assert 0<=job["priority_score"]<=100;assert job["priority_label"]=="apply_now";db.close()
def test_fresh_job_ranks_above_stale_equal_match(tmp_path):
    db=Database(tmp_path/"jobs.db");fresh=make_job(db,"Fresh Role",80,days_old=0);stale=make_job(db,"Stale Role",80,days_old=30);jobs=db.list_jobs();assert jobs[0]["id"]==fresh;assert jobs[0]["priority_score"]>db.get_job(stale)["priority_score"];db.close()
def test_higher_match_can_outweigh_small_freshness_difference(tmp_path):
    db=Database(tmp_path/"jobs.db");strong=make_job(db,"Strong Match",95,days_old=7);weak=make_job(db,"Weak Match",60,days_old=0);assert db.list_jobs()[0]["id"]==strong;assert db.get_job(strong)["priority_score"]>db.get_job(weak)["priority_score"];db.close()
def test_application_state_reduces_apply_now_priority(tmp_path):
    db=Database(tmp_path/"jobs.db");new=make_job(db,"New Role",85,status="new");applied=make_job(db,"Applied Role",85,status="applied");interview=make_job(db,"Interview Role",85,status="interview");assert db.get_job(new)["priority_score"]>db.get_job(applied)["priority_score"]>db.get_job(interview)["priority_score"];db.close()
def test_inactive_job_is_deprioritized(tmp_path):
    db=Database(tmp_path/"jobs.db");active=make_job(db,"Active Role",75,active=True);expired=make_job(db,"Expired Role",75,active=False);assert db.get_job(active)["priority_score"]>db.get_job(expired)["priority_score"];assert db.list_jobs()[0]["id"]==active;db.close()
def test_priority_labels_cover_thresholds():
    assert Database._priority_label(80)=="apply_now";assert Database._priority_label(79.9)=="high";assert Database._priority_label(65)=="high";assert Database._priority_label(64.9)=="medium";assert Database._priority_label(45)=="medium";assert Database._priority_label(44.9)=="low"
def test_priority_score_is_bounded():
    base={"last_seen_at":datetime.now(timezone.utc).isoformat(),"application_status":"new","is_active":True};assert Database._priority({**base,"match_score":500})<=100;assert Database._priority({**base,"match_score":-500})>=0
def test_list_jobs_limit_applies_after_priority_ranking(tmp_path):
    db=Database(tmp_path/"jobs.db");make_job(db,"Low",20);best=make_job(db,"Best",99);make_job(db,"Middle",60);jobs=db.list_jobs(limit=1);assert len(jobs)==1;assert jobs[0]["id"]==best;db.close()
def test_priority_recalculates_after_status_change(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=make_job(db,"Changing Role",90);before=db.get_job(job_id)["priority_score"];db.update_application_status(job_id,"applied");after=db.get_job(job_id)["priority_score"];assert after<before;db.close()
def test_priority_recalculates_when_job_expires_and_reactivates(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=make_job(db,"Lifecycle Role",90);active_score=db.get_job(job_id)["priority_score"];db.mark_missing_jobs_inactive([],platform="greenhouse");expired_score=db.get_job(job_id)["priority_score"];assert expired_score<active_score;db.save_job({"title":"Lifecycle Role","company":"Priority Co","location":"Remote","apply_url":"https://example.com/lifecycle-role","platform":"greenhouse"},match={"score":90});assert db.get_job(job_id)["priority_score"]>expired_score;db.close()
def test_save_and_get_job(tmp_path):
    db=Database(tmp_path/"jobs.db");job=Job(title="QA Automation Engineer",company="Example",location="Bengaluru",apply_url="https://example.com/jobs/1",description="Python Selenium Pytest",platform="greenhouse");job_id=db.save_job(job,match={"score":75.0,"matched_skills":["python","selenium","pytest"],"missing_skills":["docker"]});stored=db.get_job(job_id);assert stored["match_score"]==75.0;assert stored["application_status"]=="new";assert stored["is_active"] is True;assert "priority_score" in stored;assert "priority_label" in stored;db.close()
def test_duplicate_apply_url_updates_existing_job(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/jobs/1";a=db.save_job({"title":"QA Engineer","company":"Example","apply_url":url},match={"score":50});b=db.save_job({"title":"Senior QA Engineer","company":"Example","apply_url":url},match={"score":90});assert a==b;assert len(db.list_jobs())==1;assert db.get_job(a)["match_score"]==90;db.close()
def test_cross_source_duplicate_collapses_to_one_job(tmp_path):
    db=Database(tmp_path/"jobs.db");first="https://boards.greenhouse.io/acme/jobs/123";second="https://acme.wd5.myworkdayjobs.com/Careers/job/123";a=db.save_job({"title":"QA Automation Engineer","company":"Acme Ltd.","location":"Bengaluru","apply_url":first,"platform":"greenhouse"},match={"score":80});b=db.save_job({"title":"QA-Automation Engineer","company":"ACME LTD","location":"Bengaluru","apply_url":second,"platform":"workday"},match={"score":91});assert a==b;assert set(db.get_job(a)["source_urls"])=={first,second};db.close()
def test_deduplication_keeps_different_locations_separate(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"QA Engineer","company":"Acme","location":"Bengaluru","apply_url":"https://example.com/blr"});db.save_job({"title":"QA Engineer","company":"Acme","location":"Pune","apply_url":"https://example.com/pune"});assert len(db.list_jobs())==2;db.close()
def test_cross_source_duplicate_preserves_tracking(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.save_job({"title":"Senior QA Engineer","company":"Acme","location":"Remote","apply_url":"https://example.com/one"});db.update_application_status(a,"interview");db.update_job_tracking(a,saved=True,notes="Recruiter: Priya");b=db.save_job({"title":"Senior QA Engineer","company":"Acme","location":"Remote","apply_url":"https://example.net/two"},match={"score":95});stored=db.get_job(b);assert a==b;assert stored["application_status"]=="interview";assert stored["is_saved"] is True;assert stored["notes"]=="Recruiter: Priya";db.close()
def test_mark_missing_jobs_inactive_and_filter(tmp_path):
    db=Database(tmp_path/"jobs.db");keep=db.save_job({"title":"Keep","company":"Example","apply_url":"https://example.com/keep","platform":"greenhouse"});gone=db.save_job({"title":"Gone","company":"Example","apply_url":"https://example.com/gone","platform":"greenhouse"});assert db.mark_missing_jobs_inactive(["https://example.com/keep"],platform="greenhouse")==1;assert db.get_job(keep)["is_active"] is True;assert db.get_job(gone)["is_active"] is False;db.close()
def test_update_and_filter_application_status(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"});db.update_application_status(a,"interview");assert db.list_jobs(status="interview")[0]["id"]==a;db.close()
def test_invalid_application_status_rejected(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"})
    with pytest.raises(ValueError,match="Invalid application status"):db.update_application_status(job_id,"hired")
    db.close()
def test_saved_job_and_notes_can_be_updated(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"QA","company":"Example","apply_url":"https://example.com/qa"});updated=db.update_job_tracking(job_id,saved=True,notes="Prepare Selenium framework examples");assert updated["is_saved"] is True;assert updated["notes"]=="Prepare Selenium framework examples";db.close()
def test_analytics_empty_database(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.get_analytics();assert a["total"]==0;assert a["active"]==0;assert a["average_match_score"]==0.0;assert a["response_rate"]==0.0;db.close()
def test_analytics_active_average_excludes_expired_jobs(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"Active","company":"Example","apply_url":"https://example.com/a","platform":"greenhouse"},match={"score":80});db.save_job({"title":"Expired","company":"Example","apply_url":"https://example.com/b","platform":"greenhouse"},match={"score":20});db.mark_missing_jobs_inactive(["https://example.com/a"],platform="greenhouse");assert db.get_analytics()["average_match_score"]==80.0;db.close()
def test_list_jobs_orders_by_match_score_when_freshness_equal(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"A","company":"A","apply_url":"https://example.com/a"},match={"score":40});db.save_job({"title":"B","company":"B","apply_url":"https://example.com/b"},match={"score":85});assert [j["title"] for j in db.list_jobs()]==["B","A"];db.close()
def test_save_job_requires_apply_url(tmp_path):
    db=Database(tmp_path/"jobs.db")
    with pytest.raises(ValueError,match="apply_url"):db.save_job({"title":"QA","company":"Example"})
    db.close()
def test_existing_database_is_migrated_without_losing_jobs(tmp_path):
    path=tmp_path/"legacy.db";conn=sqlite3.connect(path);conn.execute("""CREATE TABLE jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,location TEXT NOT NULL DEFAULT '',apply_url TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unknown',match_score REAL NOT NULL DEFAULT 0,matched_skills TEXT NOT NULL DEFAULT '[]',missing_skills TEXT NOT NULL DEFAULT '[]',discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""");conn.execute("INSERT INTO jobs(title,company,apply_url) VALUES(?,?,?)",("Legacy QA","Example","https://example.com/legacy"));conn.commit();conn.close();db=Database(path);stored=db.get_job(1);assert stored["is_active"] is True;assert stored["job_key"]=="example|legacy qa|";assert "priority_score" in stored;db.close()
