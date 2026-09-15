"""Tests for the single-user browser setup workflow."""
from io import BytesIO
import importlib

from dashboard.app import app


def test_setup_endpoint_without_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().get("/api/setup")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["resume"]["configured"] is False
    assert payload["resume"]["roles"] == []
    assert payload["preferences"]["min_match_score"] == 60.0
    assert payload["career_urls"] == []
    assert "Mumbai" in payload["available_locations"]


def test_preferences_are_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    client = app.test_client()
    client.post(
        "/api/resume",
        data={"resume": (BytesIO(b"QA Automation Engineer\nSystem Validation Engineer\nPython Selenium"), "resume.txt")},
        content_type="multipart/form-data",
    )
    response = client.patch(
        "/api/preferences",
        json={
            "career_urls": ["https://example.com/careers"],
            "target_titles": ["QA Automation Engineer"],
            "preferred_locations": ["Mumbai", "Pune"],
            "work_modes": ["hybrid"],
            "desired_keywords": ["python", "selenium"],
            "excluded_keywords": ["intern"],
            "min_match_score": 70,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["career_urls"] == ["https://example.com/careers"]
    assert payload["preferences"]["target_titles"] == ["QA Automation Engineer"]
    assert payload["preferences"]["preferred_locations"] == ["Mumbai", "Pune"]
    assert payload["preferences"]["min_match_score"] == 70.0
    reloaded = client.get("/api/setup").get_json()
    assert reloaded["preferences"]["desired_keywords"] == ["python", "selenium"]


def test_preferences_reject_invalid_url(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().patch("/api/preferences", json={"career_urls": ["http://"]})
    assert response.status_code == 400


def test_preferences_reject_manual_target_role_not_in_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    client = app.test_client()
    client.post(
        "/api/resume",
        data={"resume": (BytesIO(b"QA Automation Engineer\nPython Selenium"), "resume.txt")},
        content_type="multipart/form-data",
    )
    response = client.patch("/api/preferences", json={"target_titles": ["Unrelated Role"]})
    assert response.status_code == 400
    assert "detected in the active resume" in response.get_json()["error"]


def test_preferences_reject_invalid_location(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().patch("/api/preferences", json={"preferred_locations": ["Made Up City"]})
    assert response.status_code == 400


def test_resume_upload_parses_and_activates(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().post(
        "/api/resume",
        data={"resume": (BytesIO(b"QA Automation Engineer\nPython Selenium pytest automotive testing"), "my-resume.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    payload = response.get_json()["resume"]
    assert payload["filename"] == "my-resume.txt"
    assert "python" in payload["skills"]
    assert "selenium" in payload["skills"]
    assert "QA Automation Engineer" in payload["roles"]
    assert app.test_client().get("/api/setup").get_json()["resume"]["configured"] is True


def test_resume_upload_accepts_extensionless_pdf_from_mobile(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    pdf_bytes = b"%PDF-1.7\nmobile resume bytes\n%%EOF"
    monkeypatch.setattr(
        "matcher.resume_parser.ResumeParser.parse",
        lambda self, path: {"text": "Python Selenium", "skills": ["python", "selenium"], "roles": []},
    )
    response = app.test_client().post(
        "/api/resume",
        data={"resume": (BytesIO(pdf_bytes), "Akash_Kumar_updated", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    payload = response.get_json()["resume"]
    assert payload["filename"] == "Akash_Kumar_updated"
    assert payload["format"] == "pdf"
    active = tmp_path / "resumes" / "active.pdf"
    assert active.read_bytes() == pdf_bytes


def test_resume_upload_rejects_unsupported_format(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().post(
        "/api/resume",
        data={"resume": (BytesIO(b"not a resume"), "resume.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "Unsupported resume format" in response.get_json()["error"]


def test_discovery_requires_resume_and_url(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    client = app.test_client()
    assert client.post("/api/discovery", json={}).status_code == 400
    client.patch("/api/preferences", json={"career_urls": ["https://example.com/careers"]})
    response = client.post("/api/discovery", json={})
    assert response.status_code == 400
    assert "Upload a resume" in response.get_json()["error"]


def test_discovery_runs_existing_pipeline(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    dashboard_module = importlib.import_module("dashboard.app")
    monkeypatch.setattr(
        dashboard_module,
        "run_once",
        lambda urls, settings: {"sources": len(urls), "jobs_found": 2, "jobs_saved": 2, "jobs_skipped": 0, "errors": []},
    )
    client = app.test_client()
    client.patch("/api/preferences", json={"career_urls": ["https://example.com/careers"]})
    client.post(
        "/api/resume",
        data={"resume": (BytesIO(b"Python Selenium pytest"), "resume.txt")},
        content_type="multipart/form-data",
    )
    response = client.post("/api/discovery", json={})
    assert response.status_code == 200
    assert response.get_json()["summary"]["jobs_saved"] == 2
