from dashboard.app import app
from crawler.source_reliability import SourceMetrics


def test_source_reliability_endpoint_returns_metrics():
    app.config["SOURCE_RELIABILITY_PROVIDER"] = lambda: (
        SourceMetrics("adzuna", runs=2, successes=1, failures=1, jobs_returned=3),
    )
    try:
        response = app.test_client().get("/api/source-reliability")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["sources"][0]["source"] == "adzuna"
        assert payload["sources"][0]["runs"] == 2
        assert payload["sources"][0]["failures"] == 1
        assert payload["sources"][0]["success_rate"] == 50.0
    finally:
        app.config.pop("SOURCE_RELIABILITY_PROVIDER", None)
