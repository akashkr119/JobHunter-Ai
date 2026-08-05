"""Conservative fallback scraper for ordinary server-rendered career pages."""
import hashlib
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from crawler.job_scraper import Job,JobScraper

class GenericScraper(JobScraper):
    """Extract obvious job links and structured vacancy cards from generic pages."""
    JOB_HINTS=("job","jobs","career","careers","opening","openings","vacancy","vacancies","position","positions","opportunity","opportunities")
    ROLE_HINTS=("engineer","developer","manager","analyst","specialist","architect","tester","technician","consultant","lead","intern","executive","designer","validation","testing")
    EXCLUDE_HINTS=("login","sign in","privacy","terms","contact","about","home","talent community","job alert")
    CARD_SELECTORS=("article","li","tr","div[class*='job']","div[class*='career']","div[class*='vacan']","div[class*='opening']","div[class*='position']")
    def __init__(self,timeout:int=20,user_agent:str="JobHunter-AI/1.0"):
        self.timeout=timeout;self.user_agent=user_agent
    def scrape(self,career_url:str,company:str="")->list[Job]:
        url=self.validate_url(career_url);response=requests.get(url,timeout=self.timeout,headers={"User-Agent":self.user_agent});response.raise_for_status();return self.parse(response.text,url,company)
    def parse(self,html:str,career_url:str,company:str="")->list[Job]:
        soup=BeautifulSoup(html or "","html.parser");company=(company or self._company_from_url(career_url)).strip();jobs=[];seen=set()
        for a in soup.find_all("a",href=True):
            title=self._clean(a.get_text(" ",strip=True));href=str(a.get("href") or "").strip()
            if not self._looks_like_job(title,href):continue
            try:job=self.make_job(title=title,company=company,location=self._nearby_location(a),apply_url=href,base_url=career_url,platform="generic")
            except ValueError:continue
            self._append(jobs,seen,job)
        for node in soup.select(",".join(self.CARD_SELECTORS)):
            text=self._clean(node.get_text(" ",strip=True))
            if not self._looks_like_card(text):continue
            title=self._card_title(node,text)
            if not title:continue
            link=node.find("a",href=True);apply_url=str(link.get("href")) if link else self._synthetic_url(career_url,title,text)
            try:job=self.make_job(title=title,company=company,location=self._location_from_text(text),apply_url=apply_url,base_url=career_url,description=text,platform="generic")
            except ValueError:continue
            self._append(jobs,seen,job)
        return jobs
    @staticmethod
    def _append(jobs,seen,job):
        key=(job.apply_url.casefold(),job.title.casefold())
        if key not in seen:seen.add(key);jobs.append(job)
    def _looks_like_job(self,title:str,href:str)->bool:
        low=title.casefold();link=href.casefold()
        if len(title)<4 or len(title)>180 or any(x in low for x in self.EXCLUDE_HINTS):return False
        hint=any(x in link for x in ("/job/","/jobs/","jobid","job-id","job_id","/position/","/vacancy/","/opportunity/"))
        return hint or (any(x in low for x in self.ROLE_HINTS) and any(x in link for x in self.JOB_HINTS))
    def _looks_like_card(self,text:str)->bool:
        low=text.casefold()
        if len(text)<12 or len(text)>1200 or any(x in low for x in self.EXCLUDE_HINTS):return False
        role=any(x in low for x in self.ROLE_HINTS);context=any(x in low for x in ("location","experience","qualification","apply","responsibil","requirement","department","opening","vacancy"))
        return role and context
    def _card_title(self,node,text:str)->str:
        for tag in ("h1","h2","h3","h4","strong","b"):
            candidate=node.find(tag)
            if candidate:
                title=self._clean(candidate.get_text(" ",strip=True))
                if 4<=len(title)<=180 and any(x in title.casefold() for x in self.ROLE_HINTS):return title
        pieces=re.split(r"[|•\n]",text)
        for piece in pieces:
            title=self._clean(piece)
            if 4<=len(title)<=180 and any(x in title.casefold() for x in self.ROLE_HINTS):return title
        return ""
    @staticmethod
    def _synthetic_url(career_url,title,text):
        digest=hashlib.sha1(f"{title}|{text}".encode("utf-8")).hexdigest()[:12];return f"{career_url.rstrip('/')}#job-{digest}"
    @staticmethod
    def _clean(value):return re.sub(r"\s+"," ",str(value or "")).strip()
    @staticmethod
    def _location_from_text(text:str)->str:
        # BeautifulSoup's get_text separator is collapsed above, so stop before the
        # next common vacancy field label rather than consuming the whole card.
        match=re.search(r"(?:location|city)\s*[:\-]\s*(.+?)(?=\s+(?:experience|qualification|requirements?|responsibilities|department|apply|opening|vacancy)\s*[:\-]|$)",text,re.I)
        return match.group(1).strip(" ,;|•") if match else ""
    @classmethod
    def _nearby_location(cls,anchor)->str:
        parent=anchor.parent
        if not parent:return ""
        text=cls._clean(parent.get_text(" ",strip=True));return cls._location_from_text(text) if len(text)<=250 else ""
    @staticmethod
    def _company_from_url(url:str)->str:
        host=(urlparse(url).hostname or "Company").lower().removeprefix("www.");return host.split(".")[0].replace("-"," ").title()
