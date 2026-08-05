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
    db=Database(tmp_path/"jobs.db");job=Job(title="QA Automation Engineer",company="Example",location="Bengaluru",apply_url="https://example.com/jobs/1",description="Python Selenium Pytest",platform="greenhouse");job_id=db.save_job(job,match={"score":75.0,"matched_skills":["python","selenium","pytest"],"missing_skills":["docker"],"required_skills":["python","selenium"],"preferred_skills":["docker"],"general_skills":["pytest"],"matched_required_skills":["python","selenium"],"missing_required_skills":[]});stored=db.get_job(job_id);assert stored["match_score"]==75.0;assert stored["application_status"]=="new";assert stored["is_saved"] is False;assert stored["notes"]=="";assert stored["is_active"] is True;assert stored["last_seen_at"];assert stored["source_urls"]==[job.apply_url];db.close()
def test_duplicate_apply_url_updates_existing_job(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/jobs/1";first_id=db.save_job({"title":"QA Engineer","company":"Example","apply_url":url},match={"score":50});second_id=db.save_job({"title":"Senior QA Engineer","company":"Example","apply_url":url},match={"score":90});assert first_id==second_id;assert len(db.list_jobs())==1;assert db.get_job(first_id)["match_score"]==90;db.close()
def test_cross_source_duplicate_collapses_to_one_job(tmp_path):
    db=Database(tmp_path/"jobs.db");first="https://boards.greenhouse.io/acme/jobs/123";second="https://acme.wd5.myworkdayjobs.com/Careers/job/123";a=db.save_job({"title":"QA Automation Engineer","company":"Acme Ltd.","location":"Bengaluru","apply_url":first,"platform":"greenhouse"},match={"score":80});b=db.save_job({"title":"QA-Automation Engineer","company":"ACME LTD","location":"Bengaluru","apply_url":second,"platform":"workday"},match={"score":91});assert a==b;assert len(db.list_jobs())==1;stored=db.get_job(a);assert stored["apply_url"]==second;assert stored["platform"]=="workday";assert stored["match_score"]==91;assert set(stored["source_urls"])=={first,second};db.close()
def test_deduplication_keeps_different_locations_separate(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"QA Engineer","company":"Acme","location":"Bengaluru","apply_url":"https://example.com/blr"});db.save_job({"title":"QA Engineer","company":"Acme","location":"Pune","apply_url":"https://example.com/pune"});assert len(db.list_jobs())==2;db.close()
def test_cross_source_duplicate_preserves_tracking(tmp_path):
    db=Database(tmp_path/"jobs.db");first="https://example.com/one";second="https://example.net/two";job_id=db.save_job({"title":"Senior QA Engineer","company":"Acme","location":"Remote","apply_url":first,"platform":"greenhouse"});db.update_application_status(job_id,"interview");db.update_job_tracking(job_id,saved=True,notes="Recruiter: Priya");duplicate_id=db.save_job({"title":"Senior QA Engineer","company":"Acme","location":"Remote","apply_url":second,"platform":"workday"},match={"score":95});stored=db.get_job(duplicate_id);assert duplicate_id==job_id;assert stored["application_status"]=="interview";assert stored["is_saved"] is True;assert stored["notes"]=="Recruiter: Priya";assert set(stored["source_urls"])=={first,second};db.close()
def test_alias_url_counts_as_seen_for_lifecycle(tmp_path):
    db=Database(tmp_path/"jobs.db");first="https://boards.greenhouse.io/acme/1";second="https://jobs.acme.com/1";job_id=db.save_job({"title":"QA Engineer","company":"Acme","location":"Remote","apply_url":first,"platform":"greenhouse"});db.save_job({"title":"QA Engineer","company":"Acme","location":"Remote","apply_url":second,"platform":"greenhouse"});assert db.mark_missing_jobs_inactive([first],platform="greenhouse")==0;assert db.get_job(job_id)["is_active"] is True;db.close()
def test_rescrape_preserves_application_status(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/jobs/tracked";job_id=db.save_job({"title":"QA Engineer","company":"Example","apply_url":url},match={"score":70});db.update_application_status(job_id,"applied");db.save_job({"title":"Senior QA Engineer","company":"Example","apply_url":url},match={"score":92});stored=db.get_job(job_id);assert stored["application_status"]=="applied";assert stored["match_score"]==92;db.close()
def test_saved_job_and_notes_can_be_updated(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"QA","company":"Example","apply_url":"https://example.com/qa"});updated=db.update_job_tracking(job_id,saved=True,notes="Prepare Selenium framework examples");assert updated["is_saved"] is True;assert updated["notes"]=="Prepare Selenium framework examples";updated=db.update_job_tracking(job_id,saved=False);assert updated["is_saved"] is False;assert updated["notes"]=="Prepare Selenium framework examples";db.close()
def test_saved_jobs_can_be_filtered(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"});db.save_job({"title":"B","company":"Example","apply_url":"https://example.com/b"});db.update_job_tracking(a,saved=True);jobs=db.list_jobs(saved=True);assert len(jobs)==1;assert jobs[0]["id"]==a;assert db.list_jobs(saved=False)[0]["title"]=="B";db.close()
def test_tracking_requires_change_and_valid_job(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"})
    with pytest.raises(ValueError,match="saved or notes"):db.update_job_tracking(job_id)
    with pytest.raises(KeyError,match="Job not found"):db.update_job_tracking(999,saved=True)
    db.close()
def test_notes_length_is_limited(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"})
    with pytest.raises(ValueError,match="5000"):db.update_job_tracking(job_id,notes="x"*5001)
    db.close()
def test_rescrape_preserves_saved_flag_and_notes(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/keep";job_id=db.save_job({"title":"QA","company":"Example","apply_url":url},match={"score":60});db.update_job_tracking(job_id,saved=True,notes="Recruiter call Friday");db.save_job({"title":"Senior QA","company":"Example","apply_url":url,"location":"Pune"},match={"score":95});stored=db.get_job(job_id);assert stored["is_saved"] is True;assert stored["notes"]=="Recruiter call Friday";assert stored["title"]=="Senior QA";assert stored["match_score"]==95;db.close()
def test_mark_missing_jobs_inactive_and_filter(tmp_path):
    db=Database(tmp_path/"jobs.db");keep=db.save_job({"title":"Keep","company":"Example","apply_url":"https://example.com/keep","platform":"greenhouse"});gone=db.save_job({"title":"Gone","company":"Example","apply_url":"https://example.com/gone","platform":"greenhouse"});assert db.mark_missing_jobs_inactive(["https://example.com/keep"],platform="greenhouse")==1;assert db.get_job(keep)["is_active"] is True;assert db.get_job(gone)["is_active"] is False;assert [j["id"] for j in db.list_jobs(active=True)]==[keep];assert [j["id"] for j in db.list_jobs(active=False)]==[gone];db.close()
def test_rescrape_reactivates_expired_job_and_preserves_tracking(tmp_path):
    db=Database(tmp_path/"jobs.db");url="https://example.com/reopen";job_id=db.save_job({"title":"QA","company":"Example","apply_url":url,"platform":"greenhouse"});db.update_application_status(job_id,"applied");db.update_job_tracking(job_id,saved=True,notes="Already applied");db.mark_missing_jobs_inactive([],platform="greenhouse");assert db.get_job(job_id)["is_active"] is False;db.save_job({"title":"QA reopened","company":"Example","apply_url":url,"platform":"greenhouse"});stored=db.get_job(job_id);assert stored["is_active"] is True;assert stored["application_status"]=="applied";assert stored["is_saved"] is True;assert stored["notes"]=="Already applied";db.close()
def test_update_and_filter_application_status(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"});db.update_application_status(a,"interview");assert db.list_jobs(status="interview")[0]["id"]==a;db.close()
def test_invalid_application_status_rejected(tmp_path):
    db=Database(tmp_path/"jobs.db");job_id=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"})
    with pytest.raises(ValueError,match="Invalid application status"):db.update_application_status(job_id,"hired")
    db.close()
def test_unknown_job_status_update_rejected(tmp_path):
    db=Database(tmp_path/"jobs.db")
    with pytest.raises(KeyError):db.update_application_status(999,"applied")
    db.close()
def test_analytics_empty_database(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.get_analytics();assert a["total"]==0;assert a["active"]==0;assert a["inactive"]==0;assert a["new_today"]==0;assert a["saved"]==0;assert a["average_match_score"]==0.0;assert a["response_rate"]==0.0;db.close()
def test_analytics_includes_saved_count(tmp_path):
    db=Database(tmp_path/"jobs.db");a=db.save_job({"title":"A","company":"Example","apply_url":"https://example.com/a"},match={"score":80});db.save_job({"title":"B","company":"Example","apply_url":"https://example.com/b"},match={"score":60});db.update_job_tracking(a,saved=True);stats=db.get_analytics();assert stats["total"]==2;assert stats["saved"]==1;assert stats["active"]==2;assert stats["inactive"]==0;assert stats["new_today"]==2;assert stats["average_match_score"]==70.0;db.close()
def test_analytics_active_average_excludes_expired_jobs(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"Active","company":"Example","apply_url":"https://example.com/a","platform":"greenhouse"},match={"score":80});db.save_job({"title":"Expired","company":"Example","apply_url":"https://example.com/b","platform":"greenhouse"},match={"score":20});db.mark_missing_jobs_inactive(["https://example.com/a"],platform="greenhouse");stats=db.get_analytics();assert stats["active"]==1;assert stats["inactive"]==1;assert stats["average_match_score"]==80.0;db.close()
def test_list_jobs_orders_by_match_score(tmp_path):
    db=Database(tmp_path/"jobs.db");db.save_job({"title":"A","company":"A","apply_url":"https://example.com/a"},match={"score":40});db.save_job({"title":"B","company":"B","apply_url":"https://example.com/b"},match={"score":85});assert [j["title"] for j in db.list_jobs()]==["B","A"];db.close()
def test_save_job_requires_apply_url(tmp_path):
    db=Database(tmp_path/"jobs.db")
    with pytest.raises(ValueError,match="apply_url"):db.save_job({"title":"QA","company":"Example"})
    db.close()
def test_database_persists_after_reopen(tmp_path):
    path=tmp_path/"jobs.db";db=Database(path);job_id=db.save_job({"title":"Persistent","company":"Example","apply_url":"https://example.com/p"});db.update_job_tracking(job_id,saved=True,notes="Keep me");db.close();db=Database(path);stored=db.get_job(job_id);assert stored["is_saved"] is True;assert stored["notes"]=="Keep me";assert stored["is_active"] is True;assert stored["last_seen_at"];assert stored["source_urls"]==["https://example.com/p"];db.close()
def test_existing_database_is_migrated_without_losing_jobs(tmp_path):
    path=tmp_path/"legacy.db";conn=sqlite3.connect(path);conn.execute("""CREATE TABLE jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,location TEXT NOT NULL DEFAULT '',apply_url TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unknown',match_score REAL NOT NULL DEFAULT 0,matched_skills TEXT NOT NULL DEFAULT '[]',missing_skills TEXT NOT NULL DEFAULT '[]',discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""");conn.execute("INSERT INTO jobs(title,company,apply_url) VALUES(?,?,?)",("Legacy QA","Example","https://example.com/legacy"));conn.commit();conn.close();db=Database(path);columns={r["name"] for r in db.fetchall("PRAGMA table_info(jobs)")};assert {"application_status","is_saved","notes","is_active","last_seen_at","job_key"}.issubset(columns);stored=db.get_job(1);assert stored["is_saved"] is False;assert stored["notes"]=="";assert stored["is_active"] is True;assert stored["last_seen_at"];assert stored["job_key"]=="example|legacy qa|";assert stored["source_urls"]==["https://example.com/legacy"];db.close()
