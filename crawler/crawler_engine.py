"""Main crawler orchestration engine."""

from crawler.ats_router import ATSRouter
from crawler.career_finder import CareerFinder
from crawler.company_loader import CompanyLoader
from crawler.platform_detector import PlatformDetector
from crawler.website_finder import WebsiteFinder


class CrawlerEngine:
    """Coordinates the end-to-end job crawling workflow."""

    def __init__(self):
        self.loader = CompanyLoader()
        self.website_finder = WebsiteFinder()
        self.career_finder = CareerFinder()
        self.detector = PlatformDetector()
        self.router = ATSRouter()

    def run(self, excel_path: str):
        jobs = []
        companies = self.loader.load(excel_path)

        for company in companies:
            website = self.website_finder.find(company)
            career_url = self.career_finder.find(website)
            platform = self.detector.detect(career_url)
            jobs.extend(self.router.scrape(platform, career_url))

        return jobs
