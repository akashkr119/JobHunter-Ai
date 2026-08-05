from crawler.generic_scraper import GenericScraper
from crawler.scraper_factory import ScraperFactory

def test_generic_parser_extracts_obvious_job_links():
    html='''<html><body><a href="/careers/jobs/123">System Test Engineer</a><a href="/privacy">Privacy</a><a href="/about">About Us</a></body></html>'''
    jobs=GenericScraper().parse(html,"https://auto.example.com/careers","Example Auto")
    assert len(jobs)==1;assert jobs[0].title=="System Test Engineer";assert jobs[0].company=="Example Auto";assert jobs[0].apply_url=="https://auto.example.com/careers/jobs/123";assert jobs[0].platform=="generic"
def test_generic_parser_deduplicates_same_apply_url():
    html='<a href="/jobs/42">Validation Engineer</a><a href="/jobs/42">Validation Engineer</a>'
    assert len(GenericScraper().parse(html,"https://example.com/careers","Example"))==1
def test_generic_parser_ignores_navigation_links():
    html='<a href="/careers">Careers</a><a href="/jobs/alerts">Job Alert</a><a href="/contact">Contact</a>'
    assert GenericScraper().parse(html,"https://example.com/careers","Example")==[]
def test_factory_falls_back_for_unknown_platform():
    assert isinstance(ScraperFactory().from_url("https://example.com/careers"),GenericScraper)
def test_factory_falls_back_for_known_but_unimplemented_platform():
    assert isinstance(ScraperFactory().from_url("https://example.oraclecloud.com/hcmUI/CandidateExperience"),GenericScraper)
