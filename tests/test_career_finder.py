"""Unit tests for career finder."""
from unittest.mock import MagicMock,patch
import requests,pytest
from crawler.career_finder import CareerFinder

def test_career_finder_instance():assert CareerFinder() is not None
def test_has_find_method():assert hasattr(CareerFinder(),"find")
def test_find_method_is_callable():assert callable(CareerFinder().find)
def test_candidate_urls_include_common_paths():
    urls=CareerFinder().candidate_urls("example.com");assert "https://example.com/careers" in urls;assert "https://example.com/jobs" in urls
def test_discover_finds_internal_and_external_career_links():
    session=MagicMock();home=MagicMock();home.text='<a href="/careers">Careers</a><a href="https://jobs.lever.co/example">Open positions</a><a href="/about">About us</a><a href="mailto:hr@example.com">Jobs email</a>';empty=MagicMock();empty.text='';session.get.side_effect=[home,empty,empty];urls=CareerFinder(session=session).discover("https://example.com");assert "https://example.com/careers" in urls;assert "https://jobs.lever.co/example" in urls;assert "https://example.com/about" not in urls
def test_discover_resolves_relative_job_link():
    session=MagicMock();home=MagicMock();home.text='<a href="/company/jobs/search">Find Jobs</a>';empty=MagicMock();empty.text='';session.get.side_effect=[home,empty];urls=CareerFinder(session=session).discover("https://example.com");assert "https://example.com/company/jobs/search" in urls
def test_discover_follows_career_landing_to_external_job_search():
    session=MagicMock();home=MagicMock();home.text='<a href="/careers">Careers</a>';landing=MagicMock();landing.text='<a href="https://jobs.example-ats.com/search">Find A Job</a>';session.get.side_effect=[home,landing];urls=CareerFinder(session=session).discover("https://example.com");assert urls[0]=="https://jobs.example-ats.com/search";assert "https://example.com/careers" in urls
def test_discover_prefers_current_openings_destination():
    session=MagicMock();home=MagicMock();home.text='<a href="/careers">Careers</a>';landing=MagicMock();landing.text='<a href="/careers/current-openings">Current Openings</a>';session.get.side_effect=[home,landing];urls=CareerFinder(session=session).discover("https://example.com");assert urls[0]=="https://example.com/careers/current-openings"
def test_deep_discovery_failure_keeps_landing_page():
    session=MagicMock();home=MagicMock();home.text='<a href="/careers">Careers</a>';session.get.side_effect=[home,requests.RequestException("blocked")]
    with patch("crawler.career_finder.subprocess.run",side_effect=FileNotFoundError):
        assert CareerFinder(session=session).discover("https://example.com")==["https://example.com/careers"]
def test_curl_fallback_recovers_career_links():
    session=MagicMock();session.get.side_effect=requests.RequestException("blocked")
    result=MagicMock(stdout='<a href="/careers">Careers</a>')
    with patch("crawler.career_finder.subprocess.run",return_value=result) as run:
        urls=CareerFinder(session=session,timeout=7).discover("https://example.com")
    assert urls[0]=="https://example.com/careers";assert run.call_args.kwargs["timeout"]==10

def test_find_discovery_places_real_links_before_fallbacks():
    session=MagicMock();home=MagicMock();home.text='<a href="https://boards.greenhouse.io/example">Careers</a>';empty=MagicMock();empty.text='';session.get.side_effect=[home,empty];urls=CareerFinder(session=session).find("https://example.com",discover=True);assert "https://boards.greenhouse.io/example" in urls;assert "https://example.com/careers" in urls
def test_find_falls_back_when_homepage_request_fails():
    session=MagicMock();session.get.side_effect=requests.RequestException("offline")
    with patch("crawler.career_finder.subprocess.run",side_effect=FileNotFoundError):
        urls=CareerFinder(session=session).find("https://example.com",discover=True)
    assert "https://example.com/careers" in urls;assert "https://example.com/jobs" in urls
def test_find_without_discovery_does_not_make_network_request():
    session=MagicMock();finder=CareerFinder(session=session);urls=finder.find("example.com",discover=False);session.get.assert_not_called();assert urls[0]=="https://example.com/careers"
def test_discover_uses_configured_timeout_and_user_agent():
    session=MagicMock();home=MagicMock();home.text='<a href="/careers">Careers</a>';empty=MagicMock();empty.text='';session.get.side_effect=[home,empty];CareerFinder(session=session,timeout=7).discover("https://example.com");assert session.get.call_count==2
    for call in session.get.call_args_list:
        assert call.kwargs["timeout"]==7;assert "User-Agent" in call.kwargs["headers"]
@pytest.mark.parametrize("value",["","   ",None])
def test_empty_website_rejected(value):
    with pytest.raises(ValueError,match="Website URL cannot be empty"):CareerFinder().candidate_urls(value)
