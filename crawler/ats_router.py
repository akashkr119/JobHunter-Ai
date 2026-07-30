"""Route scraping requests to the correct ATS scraper."""

from crawler.ashby_scraper import AshbyScraper
from crawler.greenhouse_scraper import GreenhouseScraper
from crawler.icims_scraper import ICIMSScraper
from crawler.job_scraper import Job
from crawler.lever_scraper import LeverScraper
from crawler.oracle_scraper import OracleScraper
from crawler.smartrecruiters_scraper import SmartRecruitersScraper
from crawler.successfactors_scraper import SuccessFactorsScraper
from crawler.workday_scraper import WorkdayScraper


class ATSRouter:
    """Dispatch scraping to the appropriate ATS implementation."""

    def __init__(self):
        self.scrapers = {
            "workday": WorkdayScraper(),
            "greenhouse": GreenhouseScraper(),
            "lever": LeverScraper(),
            "smartrecruiters": SmartRecruitersScraper(),
            "icims": ICIMSScraper(),
            "successfactors": SuccessFactorsScraper(),
            "ashby": AshbyScraper(),
            "oracle": OracleScraper(),
        }

    def scrape(self, platform: str, career_url: str) -> list[Job]:
        scraper = self.scrapers.get(platform.lower())
        if scraper is None:
            raise ValueError(f"Unsupported ATS: {platform}")
        return scraper.scrape(career_url)
