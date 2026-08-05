from tools.production_smoke_test import inspect_company,write_csv

class Finder:
    def find(self,website,discover=True):return ["https://jobs.example.com/openings"]
class Detector:
    def detect(self,url,page_content=None):return "greenhouse"
class Scraper:
    def scrape(self,url,company=""):return [{"title":"QA Engineer"}]
class Factory:
    detector=Detector()
    def from_url(self,url,page_content=None):return Scraper()

def test_smoke_report_records_success_without_database_or_notifier():
    row=inspect_company({"company":"Example Motors","website":"https://example.com","career_url":None},Finder(),Factory())
    assert row["company"]=="Example Motors";assert row["career_url"]=="https://jobs.example.com/openings";assert row["platform"]=="greenhouse";assert row["scraper"]=="Scraper";assert row["jobs_found"]==1;assert row["status"]=="success";assert row["error"]==""

def test_smoke_report_records_zero_jobs():
    class EmptyScraper:
        def scrape(self,url,company=""):return []
    class EmptyFactory(Factory):
        def from_url(self,url,page_content=None):return EmptyScraper()
    row=inspect_company({"company":"Example","website":"https://example.com","career_url":None},Finder(),EmptyFactory())
    assert row["status"]=="zero_jobs";assert row["jobs_found"]==0

def test_smoke_report_records_failure_instead_of_crashing():
    class BrokenFinder:
        def find(self,website,discover=True):raise RuntimeError("blocked")
    row=inspect_company({"company":"Example","website":"https://example.com","career_url":None},BrokenFinder(),Factory())
    assert row["status"]=="failure";assert "blocked" in row["error"]

def test_smoke_report_prefers_explicit_career_url():
    class MustNotRunFinder:
        def find(self,*args,**kwargs):raise AssertionError("finder should not run")
    row=inspect_company({"company":"Example","website":"https://example.com","career_url":"https://jobs.example.com/direct"},MustNotRunFinder(),Factory())
    assert row["career_url"]=="https://jobs.example.com/direct";assert row["status"]=="success"

def test_write_csv(tmp_path):
    path=tmp_path/"report.csv";write_csv([{"company":"Example","website":"https://example.com","career_url":"https://jobs.example.com","platform":"unknown","scraper":"Scraper","jobs_found":2,"status":"success","error":""}],path);text=path.read_text();assert "company,website,career_url,platform,scraper,jobs_found,status,error" in text;assert "Example" in text
