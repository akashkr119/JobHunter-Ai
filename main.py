"""Command-line entry point for JobHunter AI."""

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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
BLOCKED_HOSTS = {
    "google.com", "www.google.com", "duckduckgo.com", "html.duckduckgo.com",
    "linkedin.com", "www.linkedin.com", "facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com", "youtube.com", "www.youtube.com",
    "wikipedia.org", "www.wikipedia.org", "twitter.com", "x.com",
    "indeed.com", "www.indeed.com", "naukri.com", "www.naukri.com",
    "glassdoor.com", "www.glassdoor.com", "ziprecruiter.com", "www.ziprecruiter.com",
}
ATS_HOSTS = (
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "smartrecruiters.com",
    "ashbyhq.com", "successfactors.com", "taleo.net", "icims.com", "jobvite.com",
)
CAREER_TERMS = (
    "career", "careers", "jobs", "job", "join-us", "join us", "opportunities",
    "work-with-us", "work with us", "vacancies", "open-positions", "open positions",
    "job-search", "jobsearch", "employment", "talent",
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
    """Extract result URLs and visible titles from common search-engine HTML."""
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


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().split(":", 1)[0].removeprefix("www.")


def _blocked_host(url: str) -> bool:
    host = _host(url)
    return host in {h.removeprefix("www.") for h in BLOCKED_HOSTS}


def _is_ats(url: str) -> bool:
    host = _host(url)
    return any(host == ats or host.endswith("." + ats) for ats in ATS_HOSTS)


def _candidate_score(url: str, title: str, company: str) -> int:
    """Score search results so job boards never win over official/ATS pages."""
    if _blocked_host(url):
        return -1000
    host = _host(url)
    path = urlparse(url).path.lower()
    haystack = f"{url} {title}".lower()
    score = 0
    if _is_ats(url):
        score += 100
    if any(term in path for term in CAREER_TERMS):
        score += 35
    if any(term in haystack for term in CAREER_TERMS):
        score += 20
    company_tokens = [token.lower() for token in company.replace("&", " ").split() if len(token) >= 4]
    score += min(30, sum(5 for token in company_tokens if token in host or token in title.lower()))
    if host.endswith(".gov"):
        score -= 50
    return score


def _extract_official_website(url: str) -> str | None:
    """Return the company origin for an official career URL, not for an ATS URL."""
    if _is_ats(url):
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _resolve_company_career(company: str) -> dict:
    """Find a likely official career page or ATS page for a company name.

    This is deliberately bounded: two search engines, two queries, short
    connect/read timeouts, and at most one best result. The result is later
    persisted in the user's Excel file so future runs do not search again.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "Chrome/151 Safari/537.36"
    })
    candidates: list[tuple[int, str, str]] = []
    queries = (f'"{company}" careers', f'"{company}" jobs')
    for raw_query in queries:
        query = quote_plus(raw_query)
        for engine in SEARCH_ENGINES:
            try:
                response = session.get(engine + query, timeout=(3, 7))
                response.raise_for_status()
            except requests.RequestException:
                continue
            for href, title in _search_links(response.text):
                score = _candidate_score(href, title, company)
                if score > 0:
                    candidates.append((score, href.rstrip("/"), title))
            if candidates:
                break
        if candidates:
            # The first query is preferable; don't waste time on broad searches
            # once we have a credible result.
            break

    if not candidates:
        return {"website": None, "career_url": None, "status": "Not found"}

    candidates.sort(key=lambda item: item[0], reverse=True)
    score, url, _ = candidates[0]
    if score < 35:
        return {"website": None, "career_url": None, "status": "Low confidence"}
    return {
        "website": _extract_official_website(url),
        "career_url": url,
        "status": "Found" if score >= 80 else "Found - verify",
    }


def load_career_urls(excel_path: str, discover: bool = True) -> list[str]:
    """Resolve career URLs and persist them into the same Excel workbook.

    Supported input formats:
      1. Company Name only — automatic career-page discovery is performed and
         Website/Career URL/Discovery Status/Last Checked columns are added.
      2. Company + Website — career discovery uses the supplied website.
      3. Company + Career URL — the supplied URL is used as-is.

    Once a Career URL exists in the workbook it is reused, so every scheduled
    run can go directly to the company's career source instead of rediscovering it.
    """
    loader = CompanyLoader()
    targets = loader.load_targets(excel_path)
    career_finder = CareerFinder()
    website_finder = WebsiteFinder()
    urls: list[str] = []
    seen = set()
    results: dict[str, dict] = {}
    company_only = [target for target in targets if not target.get("career_url") and not target.get("website")]

    if company_only:
        print(f"[DISCOVERY] {len(company_only)} companies have no URL. Finding career pages automatically...", flush=True)
        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="career-discovery") as pool:
            futures = {pool.submit(_resolve_company_career, target["company"]): target["company"] for target in company_only}
            completed = 0
            for future in as_completed(futures):
                company = futures[future]
                completed += 1
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"website": None, "career_url": None, "status": f"Error: {type(exc).__name__}"}
                    logging.getLogger(__name__).warning("Career discovery failed for %s: %s", company, exc)
                result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                results[company] = result
                if completed % 10 == 0 or completed == len(futures):
                    found = sum(bool(item.get("career_url")) for item in results.values())
                    print(f"[DISCOVERY] {completed}/{len(futures)} checked; career URLs found={found}", flush=True)
        loader.update_discovery_results(excel_path, results)
        print(f"[DISCOVERY] Excel updated: {excel_path}", flush=True)

    for target in targets:
        company = target["company"]
        career_url = target.get("career_url") or results.get(company, {}).get("career_url")
        website = target.get("website") or results.get(company, {}).get("website")
        if career_url:
            candidates = [website_finder.normalize_url(career_url)]
        elif website:
            candidates = career_finder.find(website_finder.normalize_url(website), discover=discover)
            # Persist discovered career destinations for the next run.
            if candidates:
                results.setdefault(company, {})["career_url"] = candidates[0]
                results.setdefault(company, {})["website"] = website
                results.setdefault(company, {})["status"] = "Found"
                results.setdefault(company, {})["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        else:
            candidates = []

        for url in candidates:
            if url not in seen:
                seen.add(url)
                urls.append(url)

    # Also persist career URLs discovered from supplied Website columns.
    if results and not company_only:
        loader.update_discovery_results(excel_path, results)
    return urls


def validate_startup(career_urls: list[str], settings: Settings) -> None:
    """Fail fast on unsafe or incomplete runtime configuration."""
    resume = Path(settings.resume_path)
    if not resume.is_file():
        raise ValueError(f"Resume file not found: {resume}")
    if not career_urls:
        raise ValueError("No career URLs could be resolved from the supplied Excel file. Check the Discovery Status column in the workbook.")
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
    parser.add_argument("--companies", help="Excel file containing Company Name, optionally Website/Career URL")
    parser.add_argument("--no-discovery", action="store_true", help="Skip homepage deep discovery when Website is supplied; company-name-only Excel still performs required career search")
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
