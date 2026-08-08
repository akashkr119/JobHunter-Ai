"""Command-line entry point for JobHunter AI."""

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import Settings
from crawler.career_finder import CareerFinder
from crawler.company_loader import CompanyLoader
from crawler.website_finder import WebsiteFinder
from database.db import Database
from matcher.resume_parser import ResumeParser
from matcher.skill_matcher import SkillMatcher
from notifier.notifier import Notifier
from runner.production_runner import ProductionRunner
from scheduler.scheduler import Scheduler


SEARCH_ENGINES = (
    "https://www.google.com/search?q=",
    "https://html.duckduckgo.com/html/?q=",
)
BLOCKED_SEARCH_HOSTS = {
    "google.com", "www.google.com", "duckduckgo.com", "html.duckduckgo.com",
    "linkedin.com", "www.linkedin.com", "facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com", "youtube.com", "www.youtube.com",
    "wikipedia.org", "www.wikipedia.org", "twitter.com", "x.com",
}
CAREER_TERMS = (
    "career", "careers", "jobs", "job", "join-us", "join us", "opportunities",
    "work-with-us", "work with us", "vacancies", "open-positions", "open positions",
)


def build_scheduler(settings: Settings) -> Scheduler:
    """Build application services from centralized settings."""
    notifier = None
    if settings.notification_channel:
        notifier = Notifier(smtp_host=settings.smtp_host, smtp_port=settings.smtp_port,
                            smtp_username=settings.smtp_username, smtp_password=settings.smtp_password,
                            smtp_sender=settings.smtp_sender, telegram_bot_token=settings.telegram_bot_token)
    return Scheduler(matcher=SkillMatcher(), database=Database(settings.database_path), notifier=notifier)


def load_resume_skills(settings: Settings) -> list[str]:
    """Parse the configured resume and return detected skills."""
    return ResumeParser().parse(settings.resume_path)["skills"]


def _search_links(html: str) -> list[tuple[str, str]]:
    """Extract ordinary result links from Google/DuckDuckGo HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        text = " ".join(anchor.stripped_strings)
        if href.startswith("/url?"):
            href = parse_qs(urlparse(href).query).get("q", [""])[0]
        if not href.startswith(("http://", "https://")):
            continue
        href = href.split("#", 1)[0]
        if href not in seen:
            seen.add(href)
            results.append((href, text))
    return results


def _blocked_search_host(url: str) -> bool:
    host = urlparse(url).netloc.lower().split(":", 1)[0]
    return host in BLOCKED_SEARCH_HOSTS or any(host.endswith("." + h) for h in BLOCKED_SEARCH_HOSTS)


def _resolve_company_career_url(company: str) -> str | None:
    """Best-effort bounded search for a company's official career/ATS page."""
    query = quote_plus(f'"{company}" careers jobs')
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"})
    for engine in SEARCH_ENGINES:
        try:
            response = session.get(engine + query, timeout=(4, 8))
            response.raise_for_status()
        except requests.RequestException:
            continue
        for href, text in _search_links(response.text):
            if _blocked_search_host(href):
                continue
            haystack = f"{href} {text}".lower()
            if not any(term in haystack for term in CAREER_TERMS):
                continue
            try:
                parsed = urlparse(href)
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    return href.rstrip("/")
            except ValueError:
                continue
    return None


def load_career_urls(excel_path: str, discover: bool = True) -> list[str]:
    """Resolve career URLs from structured or company-name-only Excel input."""
    targets = CompanyLoader().load_targets(excel_path)
    career_finder = CareerFinder()
    website_finder = WebsiteFinder()
    urls = []
    seen = set()
    company_only = [t for t in targets if not t.get("career_url") and not t.get("website")]

    if company_only:
        print(f"[DISCOVERY] {len(company_only)} company names have no URL; resolving career pages via bounded search...", flush=True)
        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="company-search") as pool:
            futures = {pool.submit(_resolve_company_career_url, t["company"]): t["company"] for t in company_only}
            resolved = {}
            completed = 0
            for future in as_completed(futures):
                company = futures[future]
                completed += 1
                try:
                    resolved[company] = future.result()
                except Exception as exc:
                    resolved[company] = None
                    logging.getLogger(__name__).warning("Career search failed for %s: %s", company, exc)
                if completed % 10 == 0 or completed == len(futures):
                    found = sum(1 for value in resolved.values() if value)
                    print(f"[DISCOVERY] searched {completed}/{len(futures)} companies; career URLs found={found}", flush=True)
    else:
        resolved = {}

    for target in targets:
        career_url = target.get("career_url")
        if career_url:
            candidates = [website_finder.normalize_url(career_url)]
        elif target.get("website"):
            candidates = career_finder.find(
                website_finder.find(target["company"], target["website"]),
                discover=discover,
            )
        elif resolved.get(target["company"]):
            # A search result is already a career/ATS destination; don't scrape
            # the company homepage just to rediscover the same link.
            candidates = [website_finder.normalize_url(resolved[target["company"]])]
        else:
            candidates = []

        for url in candidates:
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def validate_startup(career_urls: list[str], settings: Settings) -> None:
    """Fail fast on unsafe or incomplete runtime configuration."""
    resume = Path(settings.resume_path)
    if not resume.is_file():
        raise ValueError(f"Resume file not found: {resume}")
    if not career_urls:
        raise ValueError("No career URLs could be resolved from the supplied Excel file. Add a 'Website' or 'Career URL' column, or use company names that have public career pages.")
    for url in career_urls:
        parsed = urlparse(str(url).strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid career URL: {url}")
    Path(settings.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    if settings.run_history_path:
        Path(settings.run_history_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    if settings.run_lock_path:
        Path(settings.run_lock_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    settings.notification_config()


def run_once(career_urls: list[str], settings: Settings) -> dict:
    """Execute one complete discovery run."""
    scheduler = build_scheduler(settings)
    try:
        return scheduler.run_pipeline(career_urls=career_urls, resume_skills=load_resume_skills(settings),
                                      min_score=settings.min_match_score, notification=settings.notification_config(),
                                      preferences=settings.job_preferences())
    finally:
        scheduler.database.close()


def run_scheduled(career_urls: list[str], settings: Settings) -> None:
    """Run continuously with production lifecycle safeguards."""
    scheduler = build_scheduler(settings)
    runner = ProductionRunner(scheduler, career_urls, load_resume_skills(settings), settings)
    runner.start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JobHunter AI job discovery pipeline")
    parser.add_argument("career_urls", nargs="*", help="Company career/ATS URLs to scan")
    parser.add_argument("--companies", help="Excel file containing Company, Website and/or Career URL columns")
    parser.add_argument("--no-discovery", action="store_true", help="Do not fetch company homepages; company-only Excel inputs still use search-engine career resolution")
    parser.add_argument("--scheduled", action="store_true", help="Run continuously using the production runner and JOBHUNTER_SCHEDULER_HOURS")
    parser.add_argument("--env-file", default=None, help="Optional path to a .env configuration file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        settings = Settings.from_env(args.env_file)
        logging.basicConfig(level=getattr(logging, str(getattr(settings, "log_level", "INFO")).upper(), logging.INFO),
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")
        career_urls = list(args.career_urls)
        if args.companies:
            career_urls.extend(load_career_urls(args.companies, discover=not args.no_discovery))
        career_urls = list(dict.fromkeys(career_urls))
        validate_startup(career_urls, settings)
        if args.scheduled:
            run_scheduled(career_urls, settings)
            return 0
        summary = run_once(career_urls, settings)
        print("JobHunter run complete: "
              f"found={summary['jobs_found']} saved={summary['jobs_saved']} "
              f"skipped={summary['jobs_skipped']} notifications={summary['notifications_sent']} "
              f"errors={len(summary['errors'])}")
        return 0 if not summary["errors"] else 1
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
