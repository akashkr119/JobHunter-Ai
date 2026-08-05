"""Unit tests for dashboard UI and API."""
from database.db import Database
from dashboard.app import app

def _seed_database(path):
    db=Database(path);high_id=db.save_job({"title":"QA Automation Engineer","company":"Example","location":"Bengaluru","apply_url":"https://example.com/jobs/qa","description":"Python Selenium Pytest Docker","platform":"greenhouse"},match={"score":90.0,"matched_skills":["python","selenium","pytest"],"missing_skills":["docker"],"required_skills":["python","selenium","docker"],"preferred_skills":["pytest"],"matched_required_skills":["python","selenium"],"missing_required_skills":["docker"]});db.save_job({"title":"DevOps Engineer","company":"Other","apply_url":"https://example.com/jobs/devops","platform":"lever"},match={"score":40.0});db.close();return high_id

def test_app_exists():assert app is not None
def test_app_has_test_client():assert hasattr(app,"test_client")
def test_test_client_callable():assert callable(app.test_client)
def test_homepage_renders_visual_dashboard():
    response=app.test_client().get("/");html=response.get_data(as_text=True);assert response.status_code==200;assert "JobHunter AI" in html;assert 'id="search"' in html;assert 'id="score"' in html;assert 'id="platform"' in html;assert 'id="status"' in html;assert 'id="lifecycle"' in html;assert 'id="savedFilter"' in html;assert 'id="stats"' in html;assert "/api/analytics" in html;assert "/tracking" in html;assert "Active jobs" in html;assert "Expired jobs" in html;assert "New today" in html;assert "Save notes" in html;assert "Saved jobs" in html;assert "Apply" in html
def test_health_endpoint():
    r=app.test_client().get("/health");assert r.status_code==200;assert r.get_json()=={"status":"healthy"}
def test_analytics_endpoint_empty_database(tmp_path,monkeypatch):
    path=tmp_path/"empty.db";Database(path).close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));a=app.test_client().get("/api/analytics").get_json();assert a["total"]==0;assert a["active"]==0;assert a["inactive"]==0;assert a["new_today"]==0;assert a["saved"]==0;assert a["average_match_score"]==0.0
def test_analytics_endpoint_reflects_status_changes(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();assert client.get("/api/analytics").get_json()["new"]==2;client.patch(f"/api/jobs/{job_id}/status",json={"status":"interview"});assert client.get("/api/analytics").get_json()["interview"]==1
def test_jobs_endpoint_returns_tracking_fields(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));payload=app.test_client().get("/api/jobs").get_json();job=payload["jobs"][0];assert payload["count"]==2;assert job["title"]=="QA Automation Engineer";assert job["is_saved"] is False;assert job["notes"]=="";assert job["is_active"] is True;assert job["last_seen_at"];assert job["missing_required_skills"]==["docker"]
def test_active_and_expired_jobs_api_filter(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);db=Database(path);db.mark_missing_jobs_inactive([],platform="greenhouse");db.close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();active=client.get("/api/jobs?active=true").get_json();expired=client.get("/api/jobs?active=false").get_json();assert active["count"]==1;assert active["jobs"][0]["platform"]=="lever";assert expired["count"]==1;assert expired["jobs"][0]["platform"]=="greenhouse";assert expired["jobs"][0]["is_active"] is False
def test_lifecycle_analytics_endpoint(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);db=Database(path);db.mark_missing_jobs_inactive([],platform="greenhouse");db.close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));a=app.test_client().get("/api/analytics").get_json();assert a["total"]==2;assert a["active"]==1;assert a["inactive"]==1;assert a["new_today"]==2;assert a["average_match_score"]==40.0
def test_saved_job_and_notes_api_workflow(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();r=client.patch(f"/api/jobs/{job_id}/tracking",json={"saved":True,"notes":"Review Selenium and CAN testing examples"});assert r.status_code==200;job=r.get_json();assert job["is_saved"] is True;assert job["notes"]=="Review Selenium and CAN testing examples";detail=client.get(f"/api/jobs/{job_id}").get_json();assert detail["is_saved"] is True;assert detail["notes"]==job["notes"]
def test_saved_jobs_filter(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();client.patch(f"/api/jobs/{job_id}/tracking",json={"saved":True});saved=client.get("/api/jobs?saved=true").get_json();assert saved["count"]==1;assert saved["jobs"][0]["id"]==job_id;unsaved=client.get("/api/jobs?saved=false").get_json();assert unsaved["count"]==1;assert unsaved["jobs"][0]["id"]!=job_id
def test_saved_count_updates_in_analytics(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();assert client.get("/api/analytics").get_json()["saved"]==0;client.patch(f"/api/jobs/{job_id}/tracking",json={"saved":True});assert client.get("/api/analytics").get_json()["saved"]==1;client.patch(f"/api/jobs/{job_id}/tracking",json={"saved":False});assert client.get("/api/analytics").get_json()["saved"]==0
def test_tracking_api_validation(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();assert client.patch(f"/api/jobs/{job_id}/tracking",json={}).status_code==400;assert client.patch(f"/api/jobs/{job_id}/tracking",json={"saved":"yes"}).status_code==400;r=client.patch(f"/api/jobs/{job_id}/tracking",json={"notes":"x"*5001});assert r.status_code==400;assert "5000" in r.get_json()["error"];assert client.patch("/api/jobs/999/tracking",json={"saved":True}).status_code==404
def test_boolean_query_validation(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();r=client.get("/api/jobs?saved=maybe");assert r.status_code==400;assert r.get_json()["error"]=="saved must be true or false";r=client.get("/api/jobs?active=maybe");assert r.status_code==400;assert r.get_json()["error"]=="active must be true or false"
def test_jobs_endpoint_filters_minimum_score(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));assert app.test_client().get("/api/jobs?min_score=60").get_json()["count"]==1
def test_status_update_and_filter_workflow(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();r=client.patch(f"/api/jobs/{job_id}/status",json={"status":"applied"});assert r.status_code==200;assert r.get_json()["application_status"]=="applied";assert client.get("/api/jobs?status=applied").get_json()["count"]==1
def test_status_update_validation(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();assert client.patch(f"/api/jobs/{job_id}/status",json={}).status_code==400;assert client.patch(f"/api/jobs/{job_id}/status",json={"status":"hired"}).status_code==400;assert client.patch("/api/jobs/999/status",json={"status":"applied"}).status_code==404
def test_jobs_endpoint_validates_query_parameters():
    client=app.test_client();assert client.get("/api/jobs?min_score=abc").status_code==400;assert client.get("/api/jobs?min_score=101").status_code==400;assert client.get("/api/jobs?limit=0").status_code==400;assert client.get("/api/jobs?limit=501").status_code==400
def test_job_detail_returns_full_description(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));payload=app.test_client().get(f"/api/jobs/{job_id}").get_json();assert payload["description"]=="Python Selenium Pytest Docker";assert payload["apply_url"]=="https://example.com/jobs/qa";assert payload["is_saved"] is False;assert payload["is_active"] is True;assert payload["last_seen_at"];assert payload["notes"]==""
def test_job_detail_returns_404_for_unknown_job(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";Database(path).close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));assert app.test_client().get("/api/jobs/999").status_code==404
