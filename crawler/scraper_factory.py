"""Select the correct job scraper for a detected ATS platform."""
from crawler.generic_scraper import GenericScraper
from crawler.greenhouse_scraper import GreenhouseScraper
from crawler.job_scraper import JobScraper
from crawler.lever_scraper import LeverScraper
from crawler.platform_detector import PlatformDetector
from crawler.smartrecruiters_scraper import SmartRecruitersScraper
from crawler.workday_scraper import WorkdayScraper

class ScraperFactory:
    """Create ATS-specific scrapers with a conservative generic fallback."""
    SCRAPERS={"greenhouse":GreenhouseScraper,"lever":LeverScraper,"workday":WorkdayScraper,"smartrecruiters":SmartRecruitersScraper}
    def __init__(self,detector:PlatformDetector|None=None)->None:self.detector=detector or PlatformDetector()
    def create(self,platform:str)->JobScraper:
        normalized=str(platform or "").strip().lower();scraper_class=self.SCRAPERS.get(normalized)
        if scraper_class is None:
            supported=", ".join(sorted(self.SCRAPERS));raise ValueError(f"Unsupported ATS platform: {platform!r}. Supported: {supported}")
        return scraper_class()
    def from_url(self,career_url:str,page_content:str|None=None)->JobScraper:
        """Return an ATS scraper, or generic fallback for unknown/unsupported pages."""
        platform=self.detector.detect(career_url,page_content)
        if platform in self.SCRAPERS:return self.create(platform)
        return GenericScraper()
    def scrape(self,career_url:str,company:str="",page_content:str|None=None):
        scraper=self.from_url(career_url,page_content);return scraper.scrape(career_url,company=company)
