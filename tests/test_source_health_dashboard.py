from dashboard.app import app
from crawler.source_health import SourceHealth, SourceStatus


def test_source_health_endpoint_uses_configured_sources(monkeypatch):
    monkeypatch.setenv("JOBHUNTER_SOURCES", "Adzuna, LinkedIn, Indeed")
    monkeypatch.setenv("JOBHUNTER_DISABLED_SOURCES", "Indeed")

    response = app.test_client().get("/api/source-health")

    assert response.status_code == 200
    assert response.get_json() == {
        "sources": [
            {"source": "adzuna", "status": "configured", "message": None},
            {"source": "linkedin", "status": "configured", "message": None},
            {"source": "indeed", "status": "disabled", "message": None},
        ]
    }


def test_source_health_endpoint_can_use_runtime_provider():
    app.config["SOURCE_HEALTH_PROVIDER"] = lambda: (
        SourceHealth("adzuna", SourceStatus.AVAILABLE),
        SourceHealth("linkedin", SourceStatus.FAILED, "unauthorized"),
    )
    try:
        payload = app.test_client().get("/api/source-health").get_json()
    finally:
        app.config.pop("SOURCE_HEALTH_PROVIDER", None)

    assert payload == {
        "sources": [
            {"source": "adzuna", "status": "available", "message": None},
            {"source": "linkedin", "status": "failed", "message": "unauthorized"},
        ]
    }
