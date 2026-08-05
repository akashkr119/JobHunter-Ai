from crawler.generic_scraper import GenericScraper
from crawler.scraper_factory import ScraperFactory

def test_generic_parser_extracts_obvious_job_links():
    html='<html><body><a href="/careers/jobs/123">System Test Engineer</a><a href="/privacy">Privacy</a><a href="/about">About Us</a></body></html>'
    jobs=GenericScraper().parse(html,"https://auto.example.com/careers","Example Auto");assert len(jobs)==1;assert jobs[0].title=="System Test Engineer";assert jobs[0].company=="Example Auto";assert jobs[0].apply_url=="https://auto.example.com/careers/jobs/123";assert jobs[0].platform=="generic"
def test_generic_parser_deduplicates_same_apply_url():
    html='<a href="/jobs/42">Validation Engineer</a><a href="/jobs/42">Validation Engineer</a>';assert len(GenericScraper().parse(html,"https://example.com/careers","Example"))==1
def test_generic_parser_ignores_navigation_links():
    html='<a href="/careers">Careers</a><a href="/jobs/alerts">Job Alert</a><a href="/contact">Contact</a>';assert GenericScraper().parse(html,"https://example.com/careers","Example")==[]
def test_generic_parser_extracts_text_only_vacancy_card():
    html='<div class="vacancy-card"><h3>Vehicle Validation Engineer</h3><p>Location: Bengaluru</p><p>Experience: 3-5 years</p><p>Requirements: CANoe Ethernet testing</p></div>'
    jobs=GenericScraper().parse(html,"https://example.com/careers","Example Auto");assert len(jobs)==1;job=jobs[0];assert job.title=="Vehicle Validation Engineer";assert job.location=="Bengaluru";assert "CANoe Ethernet" in job.description;assert job.apply_url.startswith("https://example.com/careers#job-")
def test_text_only_card_url_is_stable():
    html='<article><h2>ADAS Test Engineer</h2><p>Location: Pune</p><p>Experience: 4 years</p></article>';s=GenericScraper();a=s.parse(html,"https://example.com/careers","Example")[0];b=s.parse(html,"https://example.com/careers","Example")[0];assert a.apply_url==b.apply_url
def test_generic_parser_rejects_generic_marketing_card():
    html='<div class="career-card"><h3>Build your career with us</h3><p>Learn about our engineering culture and opportunities.</p></div>';assert GenericScraper().parse(html,"https://example.com/careers","Example")==[]
def test_factory_falls_back_for_unknown_platform():
    assert isinstance(ScraperFactory().from_url("https://example.com/careers"),GenericScraper)
def test_factory_falls_back_for_known_but_unimplemented_platform():
    assert isinstance(ScraperFactory().from_url("https://example.oraclecloud.com/hcmUI/CandidateExperience"),GenericScraper)
