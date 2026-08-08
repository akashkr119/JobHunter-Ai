"""Command-line entry point for JobHunter AI."""

import argparse
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

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


# Search providers are deliberately independent. Search-engine HTML changes often,
# so discovery must not depend on a single provider or a single HTML selector.
SEARCH_ENGINES = (
    "https://www.google.com/search?q=",
    "https://www.bing.com/search?q=",
    "https://html.duckduckgo.com/html/?q=",
)

BLOCKED_HOSTS = {
    "google.com", "www.google.com", "bing.com", "www.bing.com",
    "duckduckgo.com", "html.duckduckgo.com", "linkedin.com", "www.linkedin.com",
    "facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com",
    "youtube.com", "www.youtube.com", "wikipedia.org", "www.wikipedia.org",
    "twitter.com", "x.com", "indeed.com", "www.indeed.com", "naukri.com",
    "www.naukri.com", "glassdoor.com", "www.glassdoor.com",
    "ziprecruiter.com", "www.ziprecruiter.com",
}

ATS_HOSTS = (
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "smartrecruiters.com",
    "ashbyhq.com", "successfactors.com", "taleo.net", "icims.com", "jobvite.com",
)

CAREER_TERMS = (
    "career", "careers", "jobs", "job", "join-us", "join us", "opportunities",
    "work-with-us", "work with us", "vacancies", "open-positions", "open positions",
    "job-search", "jobsearch", "employment", "talent", "recruiting", "recruitment",
)

SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def build_scheduler(settings: Settings) -> Scheduler:
    """Build application services from centralized settings."""
    notifier = None
    if settings.notification_channel:
        notifier = Notifier(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_username=settings.smtp_username,
            smtp_password=settings.smtp_password,
            smtp_sender=settings.smtp_sender,
            telegram_bot_token=settings.telegram_bot_token,
        )
    return Scheduler(matcher=SkillMatcher(), database=Database(settings.database_path), notifier=notifier)


def load_resume_skills(settings: Settings) -> list[str]:
    """Parse the configured resume and return detected skills."""
    return ResumeParser().parse(settings.resume_path)["skills"]


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().split(":", 1)[0].removeprefix("www.")


def _blocked_host(url: str) -> bool:
    return _host(url) in {h.removeprefix("www.") for h in BLOCKED_HOSTS}


def _is_ats(url: str) -> bool:
    host = _host(url)
    return any(host == ats or host.endswith("." + ats) for ats in ATS_HOSTS)


def _clean_result_url(url: str) -> str | None:
    """Normalize search-engine redirects into their actual destination URL."""
    if not url:
        return None
    url = unquote(url.strip())

    # Google /url?q=..., Bing /ck/a?...&u=..., and generic query redirects.
    parsed = urlparse(url)
    if parsed.path.startswith("/url"):
        query = parse_qs(parsed.query)
        url = query.get("q", query.get("url", [""]))[0]
    elif parsed.path.startswith("/ck/a"):
        query = parse_qs(parsed.query)
        encoded = query.get("u", [""])[0]
        if encoded:
            # Bing sometimes prefixes the destination with an opaque token.
            if encoded.startswith("a1"):
                encoded = encoded[2:]
            url = unquote(encoded)

    if not url.startswith(("http://", "https://")):
        return None
    return url.split("#", 1)[0]


def _search_links(html: str) -> list[tuple[str, str]]:
    """Extract destination URLs and titles from Google, Bing and DDG HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    # Prefer semantic result containers when available, but also scan every
    # anchor as a fallback because search-engine markup changes frequently.
    anchors = soup.select("li.b_algo h2 a, .result__a, a")
    for anchor in anchors:
        href = _clean_result_url(str(anchor.get("href", "")))
        if not href:
            continue
        title = " ".join(anchor.stripped_strings)
        if href not in seen:
            seen.add(href)
            results.append((href, title))
    return results


def _candidate_score(url: str, title: str, company: str) -> int:
    """Score a search result; job boards are never accepted as company sources."""
    if _blocked_host(url):
        return -1000

    host = _host(url)
    path = urlparse(url).path.lower()
    haystack = f"{url} {title}".lower()
    normalized_company = re.sub(r"[^a-z0-9]+", " ", company.lower()).strip()
    tokens = [token for token in normalized_company.split() if len(token) >= 3]

    score = 0
    if _is_ats(url):
        score += 120
    if any(term in path for term in CAREER_TERMS):
        score += 45
    if any(term in haystack for term in CAREER_TERMS):
        score += 25
    if tokens:
        matched = sum(1 for token in tokens if token in host or token in title.lower())
        score += min(40, matched * 10)
        if all(token in haystack for token in tokens):
            score += 20
    if host.endswith(".gov"):
        score -= 50
    return score


def _extract_official_website(url: str) -> str | None:
    """Return the company origin for an official career URL, not an ATS URL."""
    if _is_ats(url):
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _resolve_company_career(company: str) -> dict:
    """Find and verify a company's official career page or ATS source.

    Company-name-only Excel files use this function. It searches multiple
    providers, scores candidates, verifies the selected destination with a
    lightweight HEAD/GET request, and returns one durable source to persist in
    the same workbook. No Selenium/browser is required for discovery.
    """
    session = requests.Session()
    session.headers.update(SEARCH_HEADERS)

    # Four focused searches cover the common naming patterns without turning a
    # 200-company workbook into hundreds of slow requests.
    queries = (
        f'"{company}" careers',
        f'"{company}" jobs',
        f'"{company}" "careers" "jobs"',
        f'"{company}" "work with us"',
    )
    candidates: dict[str, tuple[int, str]] = {}

    for raw_query in queries:
        query = quote_plus(raw_query)
        query_candidates: list[tuple[int, str, str]] = []
        for engine in SEARCH_ENGINES:
            try:
                response = session.get(engine + query, timeout=(2.5, 5.0), allow_redirects=True)
                response.raise_for_status()
            except requests.RequestException:
                continue
            for href, title in _search_links(response.text):
                score = _candidate_score(href, title, company)
                if score > 0:
                    query_candidates.append((score, href.rstrip("/"), title))
            # One working provider is enough for this query; the next provider
            # remains a fallback if this provider returned no usable candidate.
            if query_candidates:
                break

        for score, href, title in query_candidates:
            old = candidates.get(href)
            if old is None or score > old[0]:
                candidates[href] = (score, title)

        # A strong ATS result is normally definitive.
        if any(_is_ats(url) and score >= 120 for url, (score, _) in candidates.items()):
            break

    if not candidates:
        return {"website": None, "career_url": None, "status": "Not found"}

    ranked = sorted(candidates.items(), key=lambda item: item[1][0], reverse=True)
    for url, (score, title) in ranked[:8]:
        if score < 55:
            continue
        verified = _verify_career_source(session, url, company)
        if verified:
            return {
                "website": _extract_official_website(url),
                "career_url": url,
                "status": "Found" if score >= 85 else "Found - verify",
            }

    # Keep a high-confidence search result even when the destination blocks HEAD/GET.
    best_url, (best_score, _) = ranked[0]
    if best_score >= 85:
        return {
            "website": _extract_official_website(best_url),
            "career_url": best_url,
            "status": "Found - verify",
        }
    return {"website": None, "career_url": None, "status": "Low confidence"}


def _verify_career_source(session: requests.Session, url: str, company: str) -> bool:
    """Verify that a candidate is reachable and looks like a career source."""
    try:
        response = session.head(url, timeout=(2.5, 4.0), allow_redirects=True)
        if response.status_code >= 400 or not response.url:
            raise requests.RequestException(f"HTTP {response.status_code}")
        final_url = response.url
        if _is_ats(final_url):
            return True
        haystack = f"{final_url} {url}".lower()
        if any(term in haystack for term in CAREER_TERMS):
            return True
    except requests.RequestException:
        pass

    try:
        response = session.get(url, timeout=(2.5, 4.0), allow_redirects=True, stream=True)
        final_url = response.url
        content_type = response.headers.get("content-type", "").lower()
        if response.status_code < 400 and (_is_ats(final_url) or any(term in f"{final_url} {url}".lower() for term in CAREER_TERMS)):
            response.close()
            return True
        if response.status_code < 400 and "text/html" in content_type:
            # Read only a small prefix; this is discovery, not page scraping.
            chunk = next(response.iter_content(chunk_size=16384), b"")
            response.close()
            text = chunk.decode("utf-8", errors="ignore").lower()
            company_token = next((t for t in re.findall(r"[a-z0-9]{3,}", company.lower()) if len(t) >= 4), "")
            return bool(company_token and company_token in text and any(term in text for term in CAREER_TERMS))
        response.close()
    except requests.RequestException:
        return False
    return False


def load_career_urls(excel_path: str, discover: bool = True) -> list[str]:
    """Resolve career URLs and persist them into the same Excel workbook.

    Input can contain only Company Name. Website and Career URL are optional.
    Existing Career URLs are reused; company-name-only rows are automatically
    discovered and written back to the workbook before job scraping begins.
    The ``discover`` flag only controls deep discovery for an already-known
    Website. It must never disable company-name resolution.
    """
    loader = CompanyLoader()
    targets = loader.load_targets(excel_path)
    career_finder = CareerFinder()
    website_finder = WebsiteFinder()
    urls: list[str] = []
    seen: set[str] = set()
    results: dict[str, dict] = {}
    company_only = [target for target in targets if not target.get("career_url") and not target.get("website")]

    if company_only:
        print(
            f"[DISCOVERY] {len(company_only)} companies have no URL. "
            "Finding official career pages automatically...",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="career-discovery") as pool:
            futures = {
                pool.submit(_resolve_company_career, target["company"]): target["company"]
                for target in company_only
            }
            completed = 0
            for future in as_completed(futures):
                company = futures[future]
                completed += 1
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "website": None,
                        "career_url": None,
                        "status": f"Error: {type(exc).__name__}",
                    }
                    logging.getLogger(__name__).warning(
                        "Career discovery failed for %s: %s", company, exc
                    )
                result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                results[company] = result
                if completed % 10 == 0 or completed == len(futures):
                    found = sum(bool(item.get("career_url")) for item in results.values())
                    print(
                        f"[DISCOVERY] {completed}/{len(futures)} checked; "
                        f"career URLs found={found}",
                        flush=True,
                    )

        loader.update_discovery_results(excel_path, results)
        print(f"[DISCOVERY] Excel updated: {excel_path}", flush=True)

    for target in targets:
        company = target["company"]
        career_url = target.get("career_url") or results.get(company, {}).get("career_url")
        website = target.get("website") or results.get(company, {}).get("website")

        if career_url:
            candidates = [website_finder.normalize_url(career_url)]
        elif website:
            candidates = career_finder.find(
                website_finder.normalize_url(website), discover=discover
            )
            if candidates:
                results.setdefault(company, {}).update({
                    "career_url": candidates[0],
                    "website": website,
                    "status": "Found",
                    "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                })
        else:
            candidates = []

        for url in candidates:
            if url not in seen:
                seen.add(url)
                urls.append(url)

    if results and not company_only:
        loader.update_discovery_results(excel_path, results)
    return urls


def validate_startup(career_urls: list[str], settings: Settings) -> None:
    """Fail fast on unsafe or incomplete runtime configuration."""
    resume = Path(settings.resume_path)
    if not resume.is_file():
        raise ValueError(f"Resume file not found: {resume}")
    if not career_urls:
        raise ValueError(
            "No career URLs could be resolved from the supplied Excel file. "
            "Check the Discovery Status column in the workbook."
        )
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
        return scheduler.run_pipeline(
            career_urls=career_urls,
            resume_skills=load_resume_skills(settings),
            min_score=settings.min_match_score,
            notification=settings.notification_config(),
            preferences=settings.job_preferences(),
        )
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
    parser.add_argument(
        "--no-discovery",
        action="store_true",
        help="Skip homepage deep discovery when Website is supplied; company-name-only Excel still performs required career search",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run continuously using the production runner and JOBHUNTER_SCHEDULER_HOURS",
    )
    parser.add_argument("--env-file", default=None, help="Optional path to a .env configuration file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        settings = Settings.from_env(args.env_file)
        logging.basicConfig(
            level=getattr(settings, "log_level", "INFO"),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        career_urls = list(args.career_urls)
        if args.companies:
            career_urls.extend(load_career_urls(args.companies, discover=not args.no_discovery))
        career_urls = list(dict.fromkeys(career_urls))
        validate_startup(career_urls, settings)
        if args.scheduled:
            run_scheduled(career_urls, settings)
            return 0
        summary = run_once(career_urls, settings)
        print(
            "JobHunter run complete: "
            f"found={summary['jobs_found']} saved={summary['jobs_saved']} "
            f"skipped={summary['jobs_skipped']} notifications={summary['notifications_sent']} "
            f"errors={len(summary['errors'])}"
        )
        return 0 if not summary["errors"] else 1
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
