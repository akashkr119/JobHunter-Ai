"""Unit tests for dashboard UI and API."""
from database.db import Database
from dashboard.app import app

def _seed_database(path):
    db=Database(path);high_id=db.save_job({"title":"QA Automation Engineer","company":"Example","location":"Bengaluru","apply_url":"https://example.com/jobs/qa","description":"Python Selenium Pytest Docker","platform":"greenhouse"},match={"score":90.0,"matched_skills":["python","selenium","pytest"],"missing_skills":["docker"],"required_skills":["python","selenium","docker"],"preferred_skills":["pytest"],"matched_required_skills":["python","selenium"],"missing_required_skills":["docker"]});db.save_job({"title":"DevOps Engineer","company":"Other","apply_url":"https://example.com/jobs/devops","platform":"lever"},match={"score":40.0});db.close();return high_id
def test_app_exists():assert app is not None
def test_app_has_test_client():assert hasattr(app,"test_client")
def test_test_client_callable():assert callable(app.test_client)
def test_homepage_renders_visual_dashboard():
    response=app.test_client().get("/");html=response.get_data(as_text=True);assert response.status_code==200;assert "JobHunter AI" in html;assert 'id="search"' in html;assert 'id="score"' in html;assert 'id="platform"' in html;assert 'id="status"' in html;assert 'id="stats"' in html;assert "/api/analytics" in html;assert "/api/jobs?limit=500" in html;assert "/status" in html;assert "Apply" in html;assert "Missing required" in html
def test_health_endpoint():
    response=app.test_client().get("/health");assert response.status_code==200;assert response.get_json()=={"status":"healthy"}
def test_analytics_endpoint_empty_database(tmp_path,monkeypatch):
    path=tmp_path/"empty.db";Database(path).close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));response=app.test_client().get("/api/analytics");a=response.get_json();assert response.status_code==200;assert a["total"]==0;assert a["average_match_score"]==0.0;assert a["response_rate"]==0.0;assert all(a[s]==0 for s in Database.APPLICATION_STATUSES)
def test_analytics_endpoint_reflects_status_changes(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();before=client.get("/api/analytics").get_json();assert before["total"]==2;assert before["new"]==2;assert before["average_match_score"]==65.0;client.patch(f"/api/jobs/{job_id}/status",json={"status":"interview"});after=client.get("/api/analytics").get_json();assert after["new"]==1;assert after["interview"]==1;assert after["total"]==2
def test_jobs_endpoint_returns_ranked_match_explanation(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));response=app.test_client().get("/api/jobs");payload=response.get_json();assert response.status_code==200;assert payload["count"]==2;assert payload["jobs"][0]["title"]=="QA Automation Engineer";assert payload["jobs"][0]["match_score"]==90.0;assert payload["jobs"][0]["matched_skills"]==["python","selenium","pytest"];assert payload["jobs"][0]["missing_required_skills"]==["docker"];assert payload["jobs"][0]["platform"]=="greenhouse";assert payload["jobs"][0]["application_status"]=="new";assert "description" not in payload["jobs"][0]
def test_jobs_endpoint_filters_minimum_score(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));payload=app.test_client().get("/api/jobs?min_score=60").get_json();assert payload["count"]==1;assert payload["jobs"][0]["match_score"]==90.0
def test_status_update_and_filter_workflow(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();response=client.patch(f"/api/jobs/{job_id}/status",json={"status":"applied"});payload=response.get_json();assert response.status_code==200;assert payload["application_status"]=="applied";assert payload["status_updated_at"] is not None;filtered=client.get("/api/jobs?status=applied").get_json();assert filtered["count"]==1;assert filtered["jobs"][0]["id"]==job_id;assert client.get("/api/jobs?status=new").get_json()["count"]==1
def test_status_update_validation(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));client=app.test_client();missing=client.patch(f"/api/jobs/{job_id}/status",json={});assert missing.status_code==400;invalid=client.patch(f"/api/jobs/{job_id}/status",json={"status":"hired"});assert invalid.status_code==400;assert "allowed_statuses" in invalid.get_json();assert client.patch("/api/jobs/999/status",json={"status":"applied"}).status_code==404;assert client.get("/api/jobs?status=hired").status_code==400
def test_jobs_endpoint_validates_query_parameters():
    client=app.test_client();assert client.get("/api/jobs?min_score=abc").status_code==400;assert client.get("/api/jobs?min_score=101").status_code==400;assert client.get("/api/jobs?limit=0").status_code==400;assert client.get("/api/jobs?limit=501").status_code==400
def test_job_detail_returns_full_description(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";job_id=_seed_database(path);monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));response=app.test_client().get(f"/api/jobs/{job_id}");payload=response.get_json();assert response.status_code==200;assert payload["title"]=="QA Automation Engineer";assert payload["description"]=="Python Selenium Pytest Docker";assert payload["apply_url"]=="https://example.com/jobs/qa";assert payload["application_status"]=="new"
def test_job_detail_returns_404_for_unknown_job(tmp_path,monkeypatch):
    path=tmp_path/"dashboard.db";Database(path).close();monkeypatch.setenv("JOBHUNTER_DATABASE_PATH",str(path));response=app.test_client().get("/api/jobs/999");assert response.status_code==404;assert response.get_json()["error"]=="Job not found"
