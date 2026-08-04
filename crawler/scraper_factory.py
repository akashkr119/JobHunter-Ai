"""Select the correct job scraper for a detected ATS platform."""

from crawler.greenhouse_scraper import GreenhouseScraper
from crawler.job_scraper import JobScraper
from crawler.lever_scraper import LeverScraper
from crawler.platform_detector import PlatformDetector
from crawler.smartrecruiters_scraper import SmartRecruitersScraper
from crawler.workday_scraper import WorkdayScraper


class ScraperFactory:
    """Create ATS-specific scrapers from platform names or career URLs."""

    SCRAPERS = {
        "greenhouse": GreenhouseScraper,
        "lever": LeverScraper,
        "workday": WorkdayScraper,
        "smartrecruiters": SmartRecruitersScraper,
    }

    def __init__(self, detector: PlatformDetector | None = None) -> None:
        self.detector = detector or PlatformDetector()

    def create(self, platform: str) -> JobScraper:
        """Create the scraper registered for ``platform``."""
        normalized = str(platform or "").strip().lower()
        scraper_class = self.SCRAPERS.get(normalized)
        if scraper_class is None:
            supported = ", ".join(sorted(self.SCRAPERS))
            raise ValueError(
                f"Unsupported ATS platform: {platform!r}. Supported: {supported}"
            )
        return scraper_class()

    def from_url(self, career_url: str, page_content: str | None = None) -> JobScraper:
        """Detect the ATS from a career URL and return its scraper."""
        platform = self.detector.detect(career_url, page_content)
        if platform == "unknown":
            raise ValueError(f"Unable to detect supported ATS from URL: {career_url}")
        return self.create(platform)

    def scrape(
        self,
        career_url: str,
        company: str = "",
        page_content: str | None = None,
    ):
        """Detect the ATS and scrape jobs in one operation."""
        scraper = self.from_url(career_url, page_content)
        return scraper.scrape(career_url, company=company)
