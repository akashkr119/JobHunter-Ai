"""Tests for the resume-first browser setup workflow."""
from io import BytesIO

from dashboard.app import app


def test_setup_endpoint_without_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().get("/api/setup")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["resume"]["configured"] is False
    assert payload["preferences"]["min_match_score"] == 60.0
    assert payload["preferences"]["automatic_search_hours"] == 24


def test_preferences_are_persisted_without_career_urls(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    client = app.test_client()
    response = client.patch(
        "/api/preferences",
        json={
            "target_titles": ["System Validation Engineer", "SDET"],
            "preferred_locations": ["Mumbai", "Pune"],
            "work_modes": ["hybrid", "remote"],
            "desired_keywords": ["python", "selenium"],
            "excluded_keywords": ["intern"],
            "min_match_score": 70,
            "automatic_search_enabled": True,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "career_urls" not in payload
    assert payload["preferences"]["target_titles"] == ["system validation engineer", "sdet"]
    assert payload["preferences"]["preferred_locations"] == ["mumbai", "pune"]
    assert payload["preferences"]["min_match_score"] == 70.0
    assert payload["preferences"]["automatic_search_enabled"] is True


def test_preferences_reject_invalid_work_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    response = app.test_client().patch("/api/preferences", json={"work_modes": ["invalid"]})
    assert response.status_code == 400


def test_resume_upload_parses_and_detects_role(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setattr(
        "matcher.resume_parser.ResumeParser.parse",
        lambda self, path: {"text": "System Validation Engineer\nPython Selenium pytest automotive testing", "skills": ["python", "selenium"]},
    )
    response = app.test_client().post(
        "/api/resume",
        data={"resume": (BytesIO(b"System Validation Engineer\nPython Selenium pytest"), "my-resume.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    payload = response.get_json()["resume"]
    assert payload["filename"] == "my-resume.txt"
    assert "python" in payload["skills"]
    assert "System Validation Engineer" in payload["detected_target_roles"]


def test_resume_upload_accepts_extensionless_pdf_from_mobile(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    pdf_bytes = b"%PDF-1.7\nmobile resume bytes\n%%EOF"
    monkeypatch.setattr(
        "matcher.resume_parser.ResumeParser.parse",
        lambda self, path: {"text": "System Validation Engineer\nPython Selenium", "skills": ["python", "selenium"]},
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


def test_discovery_requires_resume_and_location(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    client = app.test_client()
    response = client.post("/api/discovery", json={})
    assert response.status_code == 400
    assert "Upload a resume" in response.get_json()["error"]


def test_automatic_search_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DASHBOARD_CONFIG_PATH", str(tmp_path / "settings.json"))
    client = app.test_client()
    response = client.patch("/api/automatic-search", json={"enabled": False})
    assert response.status_code == 200
    assert response.get_json()["preferences"]["automatic_search_enabled"] is False
    state = client.get("/api/automatic-search").get_json()
    assert state["enabled"] is False
    assert state["interval_hours"] == 24
