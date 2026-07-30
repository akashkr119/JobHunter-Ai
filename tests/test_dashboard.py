"""Unit tests for dashboard."""

from dashboard.app import app


def test_app_exists():
    assert app is not None


def test_app_has_test_client():
    assert hasattr(app, 'test_client')


def test_test_client_callable():
    assert callable(app.test_client)
