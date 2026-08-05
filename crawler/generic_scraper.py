"""Conservative fallback scraper for ordinary server-rendered career pages."""
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from crawler.job_scraper import Job,JobScraper

class GenericScraper(JobScraper):
    """Extract obvious job links when no supported ATS-specific scraper exists."""
    JOB_HINTS=("job","jobs","career","careers","opening","openings","vacancy","vacancies","position","positions","opportunity","opportunities")
    EXCLUDE_HINTS=("login","sign in","privacy","terms","contact","about","home","talent community","job alert")
    def __init__(self,timeout:int=20,user_agent:str="JobHunter-AI/1.0"):
        self.timeout=timeout;self.user_agent=user_agent
    def scrape(self,career_url:str,company:str="")->list[Job]:
        url=self.validate_url(career_url);response=requests.get(url,timeout=self.timeout,headers={"User-Agent":self.user_agent});response.raise_for_status();return self.parse(response.text,url,company)
    def parse(self,html:str,career_url:str,company:str="")->list[Job]:
        soup=BeautifulSoup(html or "","html.parser");company=(company or self._company_from_url(career_url)).strip();jobs=[];seen=set()
        for a in soup.find_all("a",href=True):
            title=re.sub(r"\s+"," ",a.get_text(" ",strip=True)).strip();href=str(a.get("href") or "").strip()
            if not self._looks_like_job(title,href):continue
            try:job=self.make_job(title=title,company=company,location=self._nearby_location(a),apply_url=href,base_url=career_url,platform="generic")
            except ValueError:continue
            key=job.apply_url.casefold()
            if key not in seen:seen.add(key);jobs.append(job)
        return jobs
    def _looks_like_job(self,title:str,href:str)->bool:
        low=title.casefold();link=href.casefold()
        if len(title)<4 or len(title)>180 or any(x in low for x in self.EXCLUDE_HINTS):return False
        hint=any(x in link for x in ("/job/","/jobs/","jobid","job-id","job_id","/position/","/vacancy/","/opportunity/"))
        title_hint=any(x in low for x in ("engineer","developer","manager","analyst","specialist","architect","tester","technician","consultant","lead","intern"))
        return hint or (title_hint and any(x in link for x in self.JOB_HINTS))
    @staticmethod
    def _nearby_location(anchor)->str:
        parent=anchor.parent
        if not parent:return ""
        text=re.sub(r"\s+"," ",parent.get_text(" ",strip=True)).strip()
        if len(text)>250:return ""
        match=re.search(r"(?:location|city)\s*[:\-]\s*([^|•,;]{2,80})",text,re.I)
        return match.group(1).strip() if match else ""
    @staticmethod
    def _company_from_url(url:str)->str:
        host=(urlparse(url).hostname or "Company").lower().removeprefix("www.");return host.split(".")[0].replace("-"," ").title()
