"""Milestone 4 dashboard UX regression coverage."""
from dashboard.app import app


def homepage():
    response=app.test_client().get("/")
    assert response.status_code==200
    return response.get_data(as_text=True)


def test_dashboard_has_mobile_responsive_layout():
    html=homepage()
    assert 'name="viewport"' in html
    assert '@media(max-width:600px)' in html
    assert '.breakdown{grid-template-columns:1fr}' in html


def test_dashboard_has_clear_loading_empty_and_error_states():
    html=homepage()
    assert 'Loading analytics' in html
    assert 'Loading…' in html
    assert 'No jobs match your filters.' in html
    assert 'Analytics unavailable' in html
    assert "countEl.textContent='Error'" in html


def test_dashboard_actions_are_safe_and_track_application_progress():
    html=homepage()
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html
    assert 'onclick="markViewed(' in html
    assert 'Save notes' in html
    assert 'maxlength="5000"' in html
    assert 'toggleSave(' in html
    assert 'setStatus(' in html


def test_dashboard_exposes_complete_filter_set():
    html=homepage()
    for control in ('search','score','recommendation','priority','platform','status','followUp','lifecycle','savedFilter'):
        assert f'id="{control}"' in html
    assert 'Top Pick' in html
    assert 'Strong Match' in html
    assert 'Follow-up overdue' in html
    assert 'Active jobs' in html
    assert 'Expired jobs' in html
    assert 'Saved jobs' in html


def test_dashboard_explains_ranking_without_hiding_primary_actions():
    html=homepage()
    assert 'Why this recommendation?' in html
    for factor in ('Resume fit','Preferences','Freshness','Application state','Job lifecycle'):
        assert factor in html
    assert '>Apply</a>' in html
    assert '>Details</button>' in html


def test_dashboard_reorders_after_recommendation_affecting_updates():
    html=homepage()
    assert 'const sortRender=' in html
    assert 'b.recommendation_score' in html
    assert 'sortRender();loadAnalytics()' in html
