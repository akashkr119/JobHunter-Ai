"""Utilities for locating career pages on company websites."""
from urllib.parse import urljoin,urlparse
import subprocess
import requests
from bs4 import BeautifulSoup
from config.settings import REQUEST_TIMEOUT,USER_AGENT

class CareerFinder:
    """Discover career pages, including one-hop vacancy/search destinations."""
    # Keep fallback probing deliberately small. The previous 11-path list caused
    # every company to generate a long sequence of predictable 404/timeout calls.
    COMMON_PATHS=("careers","jobs","careers/jobs","join-us")
    CAREER_KEYWORDS=("career","careers","job","jobs","join us","join-us","joinus","work with us","work-with-us","opportunities","open positions","open roles","vacancies")
    DEEP_KEYWORDS=("find a job","find jobs","search jobs","search for jobs","current openings","view openings","view all open positions","open positions","job openings","vacancies","apply now")
    MAX_LANDING_PAGES=5
    CURL_TIMEOUT_BUFFER=2

    def __init__(self,session=None,timeout:int=REQUEST_TIMEOUT):
        self.session=session or requests.Session();self.timeout=timeout

    def candidate_urls(self,website_url:str)->list[str]:
        base=self._normalize_website(website_url);return [urljoin(f"{base}/",path) for path in self.COMMON_PATHS]

    @staticmethod
    def _parse_links(html,url,keywords)->list[str]:
        soup=BeautifulSoup(html,"html.parser");found=[];seen=set()
        for anchor in soup.find_all("a",href=True):
            href=str(anchor.get("href","")).strip()
            if not href or href.startswith(("mailto:","tel:","javascript:","#")):continue
            text=" ".join(anchor.stripped_strings).lower();absolute=urljoin(f"{url.rstrip('/')}/",href);parsed=urlparse(absolute);haystack=f"{text} {parsed.path.lower()} {parsed.netloc.lower()}"
            if not any(keyword in haystack for keyword in keywords):continue
            if parsed.scheme not in {"http","https"} or not parsed.netloc:continue
            normalized=absolute.rstrip("/")
            if normalized not in seen:seen.add(normalized);found.append(normalized)
        return found

    def _fetch_links_with_curl(self,url,keywords)->list[str]:
        """Use the OS curl client as a bounded fallback for TLS/HTTP edge cases."""
        timeout=max(1,int(self.timeout+self.CURL_TIMEOUT_BUFFER))
        result=subprocess.run(
            ["curl","-L","--fail","--silent","--show-error","--max-time",str(timeout),"-A",USER_AGENT,url],
            capture_output=True,text=True,timeout=timeout+1,check=True,
        )
        return self._parse_links(result.stdout,url,keywords)

    def _fetch_links(self,url,keywords)->list[str]:
        try:
            response=self.session.get(url,timeout=self.timeout,headers={"User-Agent":USER_AGENT});response.raise_for_status();return self._parse_links(response.text,url,keywords)
        except requests.RequestException as exc:
            try:
                return self._fetch_links_with_curl(url,keywords)
            except (OSError,subprocess.SubprocessError) as fallback_exc:
                raise exc from fallback_exc

    def discover(self,website_url:str)->list[str]:
        """Discover homepage career links and one hop to actual vacancy/search pages."""
        base=self._normalize_website(website_url);first=self._fetch_links(base,self.CAREER_KEYWORDS);deep=[];seen=set(first)
        for landing in first[:self.MAX_LANDING_PAGES]:
            try:links=self._fetch_links(landing,self.DEEP_KEYWORDS)
            except requests.RequestException:continue
            for link in links:
                if link not in seen:seen.add(link);deep.append(link)
        return [*deep,*first]

    def find(self,website_url:str,discover:bool=False)->list[str]:
        candidates=self.candidate_urls(website_url)
        if not discover:return candidates
        try:discovered=self.discover(website_url)
        except requests.RequestException:discovered=[]
        return list(dict.fromkeys([*discovered,*candidates]))

    @staticmethod
    def _normalize_website(website_url:str)->str:
        if website_url is None:raise ValueError("Website URL cannot be empty")
        url=str(website_url).strip()
        if not url:raise ValueError("Website URL cannot be empty")
        if not urlparse(url).scheme:url=f"https://{url}"
        parsed=urlparse(url)
        if parsed.scheme not in {"http","https"} or not parsed.netloc:raise ValueError(f"Invalid website URL: {website_url}")
        return url.rstrip("/")
