"""Unit tests for database layer."""
import sqlite3
import pytest
from crawler.job_scraper import Job
from database.db import Database

def test_database_instance(tmp_path):
    db=Database(tmp_path/"jobs.db");assert db is not None;db.close()
def test_has_connect_method(tmp_path):
    db=Database(tmp_path/"jobs.db");assert hasattr(db,"connect");assert db.connect() is not None;db.close()
def test_has_save_job_method(tmp_path):
    db=Database(tmp_path/"jobs.db");assert hasattr(db,"save_job");assert callable(db.save_job);db.close()
def test_save_and_get_job(tmp_path):
    db=Database(tmp_path/"jobs.db");job=Job(title="QA Automation Engineer",company="Example",location="Bengaluru",apply_url="https://example.com/jobs/1",description="Python Selenium Pytest",platform="greenhouse");job_id=db.save_job(job,match={"score":75.0,"matched_skills":["python","selenium","pytest"],"missing_skills":["docker"],"required_skills":["python","selenium"],"preferred_skills":["docker"],"general_skills":["pytest"],"matched_required_skills":["python","selenium"],"missing_required_skills":[]});stored=db.get_job(job_id);assert stored["match_score"]==75.0;assert stored["matched_skills"]==["python","selenium","pytest"];assert stored["missing_skills"]==["docker"];assert stored["required_skills"]==["python","selenium"];assert stored["preferred_skills"]==["docker"];assert stored["general_skills"]==["pytest"];assert stored["matched_required_skills"]==["python","selenium"];assert stored["missing_required_skills"]==[];assert stored["platform"]=="greenhouse";assert stored["location"]=="Bengaluru";assert stored["application_status"]=="new";db.close()
def test_duplicate_apply_url_updates_existing_job(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/jobs/1";first_id=db.save_job({"title":"QA Engineer","company":"Example","location":"Pune","apply_url":url,"description":"Python","platform":"greenhouse"},match={"score":50.0});second_id=db.save_job({"title":"Senior QA Engineer","company":"Example","location":"Bengaluru","apply_url":url,"description":"Python Selenium","platform":"greenhouse"},match={"score":90.0,"missing_required_skills":["docker"]});jobs=db.list_jobs();assert len(jobs)==1;assert first_id==second_id;assert jobs[0]["title"]=="Senior QA Engineer";assert jobs[0]["match_score"]==90.0;db.close()
def test_rescrape_preserves_application_status(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/jobs/tracked";job_id=db.save_job({"title":"QA Engineer","company":"Example","apply_url":url},match={"score":70});db.update_application_status(job_id,"applied");second_id=db.save_job({"title":"Senior QA Engineer","company":"Example","apply_url":url,"location":"Bengaluru"},match={"score":92});stored=db.get_job(job_id);assert second_id==job_id;assert stored["application_status"]=="applied";assert stored["match_score"]==92.0;db.close()
def test_update_and_filter_application_status(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"},match={"score":80});db.save_job({"title":"B","company":"Example","apply_url":"https://example.com/b"},match={"score":90});updated=db.update_application_status(a,"interview");assert updated["application_status"]=="interview";assert updated["status_updated_at"] is not None;assert db.list_jobs(status="interview")[0]["id"]==a;db.close()
def test_invalid_application_status_rejected(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"});
    with pytest.raises(ValueError,match="Invalid application status"):db.update_application_status(job_id,"hired")
    with pytest.raises(ValueError,match="Invalid application status"):db.list_jobs(status="hired")
    db.close()
def test_unknown_job_status_update_rejected(tmp_path):
    db=Database(tmp_path/"jobs.db")
    with pytest.raises(KeyError,match="Job not found"):db.update_application_status(999,"applied")
    db.close()
def test_analytics_empty_database(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.get_analytics();assert a=={"total":0,"average_match_score":0.0,"new":0,"viewed":0,"applied":0,"interview":0,"rejected":0,"offer":0,"response_rate":0.0};db.close()
def test_analytics_counts_average_and_response_rate(tmp_path):
    db=Database(tmp_path/"jobs.db");ids=[]
    for i,score in enumerate((60,70,80,90),1):ids.append(db.save_job({"title":f"Job {i}","company":"Example","apply_url":f"https://example.com/{i}"},match={"score":score}))
    db.update_application_status(ids[0],"applied");db.update_application_status(ids[1],"applied");db.update_application_status(ids[2],"interview");db.update_application_status(ids[3],"offer");a=db.get_analytics();assert a["total"]==4;assert a["new"]==0;assert a["applied"]==2;assert a["interview"]==1;assert a["offer"]==1;assert a["rejected"]==0;assert a["average_match_score"]==75.0;assert a["response_rate"]==100.0;db.close()
def test_list_jobs_orders_by_match_score(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"Job A","company":"A","apply_url":"https://example.com/a"},match={"score":40});db.save_job({"title":"Job B","company":"B","apply_url":"https://example.com/b"},match={"score":85});assert [j["title"] for j in db.list_jobs()]==["Job B","Job A"];db.close()
def test_list_jobs_filters_minimum_score(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"Low","company":"A","apply_url":"https://example.com/low"},match={"score":30});db.save_job({"title":"High","company":"B","apply_url":"https://example.com/high"},match={"score":80});jobs=db.list_jobs(min_score=60);assert len(jobs)==1;assert jobs[0]["title"]=="High";db.close()
def test_save_job_requires_apply_url(tmp_path):
    db=Database(tmp_path/"jobs.db")
    with pytest.raises(ValueError,match="apply_url"):db.save_job({"title":"QA","company":"Example"})
    db.close()
def test_database_persists_after_reopen(tmp_path):
    path=tmp_path/"jobs.db";db=Database(path);job_id=db.save_job({"title":"Persistent Job","company":"Example","apply_url":"https://example.com/persistent"});db.update_application_status(job_id,"applied");db.close();reopened=Database(path);assert reopened.get_job(job_id)["title"]=="Persistent Job";assert reopened.get_job(job_id)["application_status"]=="applied";reopened.close()
def test_existing_database_is_migrated_without_losing_jobs(tmp_path):
    path=tmp_path/"legacy.db";conn=sqlite3.connect(path);conn.execute("""CREATE TABLE jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,location TEXT NOT NULL DEFAULT '',apply_url TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unknown',match_score REAL NOT NULL DEFAULT 0,matched_skills TEXT NOT NULL DEFAULT '[]',missing_skills TEXT NOT NULL DEFAULT '[]',discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""");conn.execute("INSERT INTO jobs(title,company,apply_url) VALUES(?,?,?)",("Legacy QA","Example","https://example.com/legacy"));conn.commit();conn.close();db=Database(path);columns={row["name"] for row in db.fetchall("PRAGMA table_info(jobs)")};assert {"required_skills","preferred_skills","general_skills","matched_required_skills","missing_required_skills","application_status","status_updated_at"}.issubset(columns);jobs=db.list_jobs();assert len(jobs)==1;assert jobs[0]["title"]=="Legacy QA";assert jobs[0]["application_status"]=="new";db.close()
