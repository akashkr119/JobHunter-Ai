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
from crawler.company_domain_resolver import resolve as resolve_company_domain
from crawler.company_loader import CompanyLoader
from crawler.website_finder import WebsiteFinder
from database.db import Database
from matcher.resume_parser import ResumeParser
from matcher.skill_matcher import SkillMatcher
from notifier.notifier import Notifier
from runner.production_runner import ProductionRunner
from scheduler.scheduler import Scheduler

SEARCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
BLOCKED_HOSTS = {"google.com","www.google.com","bing.com","www.bing.com","duckduckgo.com","html.duckduckgo.com","linkedin.com","www.linkedin.com","facebook.com","www.facebook.com","instagram.com","www.instagram.com","youtube.com","www.youtube.com","wikipedia.org","www.wikipedia.org","twitter.com","x.com","indeed.com","www.indeed.com","naukri.com","www.naukri.com","glassdoor.com","www.glassdoor.com","ziprecruiter.com","www.ziprecruiter.com"}
ATS_HOSTS = ("greenhouse.io","lever.co","myworkdayjobs.com","smartrecruiters.com","ashbyhq.com","successfactors.com","taleo.net","icims.com","jobvite.com")
CAREER_TERMS = ("career","careers","jobs","job","join-us","join us","opportunities","work-with-us","work with us","vacancies","open-positions","open positions","job-search","jobsearch","employment","talent","recruiting","recruitment")


def build_scheduler(settings: Settings) -> Scheduler:
    notifier = None
    if settings.notification_channel:
        notifier = Notifier(smtp_host=settings.smtp_host, smtp_port=settings.smtp_port, smtp_username=settings.smtp_username, smtp_password=settings.smtp_password, smtp_sender=settings.smtp_sender, telegram_bot_token=settings.telegram_bot_token)
    return Scheduler(matcher=SkillMatcher(), database=Database(settings.database_path), notifier=notifier)


def load_resume_skills(settings: Settings) -> list[str]:
    return ResumeParser().parse(settings.resume_path)["skills"]


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().split(":", 1)[0].removeprefix("www.")


def _blocked_host(url: str) -> bool:
    return _host(url) in {h.removeprefix("www.") for h in BLOCKED_HOSTS}


def _is_ats(url: str) -> bool:
    host = _host(url)
    return any(host == ats or host.endswith("." + ats) for ats in ATS_HOSTS)


def _clean_url(url: str) -> str | None:
    if not url:
        return None
    url = unquote(url.strip())
    parsed = urlparse(url)
    if parsed.path.startswith("/url"):
        url = parse_qs(parsed.query).get("q", parse_qs(parsed.query).get("url", [""]))[0]
    elif parsed.path.startswith("/ck/a"):
        encoded = parse_qs(parsed.query).get("u", [""])[0]
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        url = unquote(encoded)
    if not url.startswith(("http://", "https://")):
        return None
    return url.split("#", 1)[0]


def _search_html_links(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.select("li.b_algo h2 a, .result__a, a"):
        href = _clean_url(str(a.get("href", "")))
        if href and href not in seen:
            seen.add(href); out.append((href, " ".join(a.stripped_strings)))
    return out


def _candidate_score(url: str, title: str, company: str) -> int:
    if _blocked_host(url):
        return -1000
    hay = f"{url} {title}".lower(); path = urlparse(url).path.lower()
    tokens = [x for x in re.sub(r"[^a-z0-9]+", " ", company.lower()).split() if len(x) >= 3]
    score = 120 if _is_ats(url) else 0
    score += 45 if any(t in path for t in CAREER_TERMS) else 0
    score += 25 if any(t in hay for t in CAREER_TERMS) else 0
    score += min(40, sum(t in hay for t in tokens) * 10)
    if tokens and all(t in hay for t in tokens): score += 20
    return score


def _jina_results(session: requests.Session, company: str) -> list[tuple[str, str]]:
    query = quote_plus(f'"{company}" careers jobs')
    try:
        r = session.get(f"https://s.jina.ai/{query}", timeout=(3, 10)); r.raise_for_status(); text = r.text
    except requests.RequestException:
        return []
    links = []
    for line in text.splitlines():
        for match in re.findall(r"https?://[^\s)<>\]]+", line):
            url = match.rstrip(".,;\"'")
            if url.startswith("http"): links.append((url, line[:300]))
    return links


def _verify_candidate(session: requests.Session, url: str) -> bool:
    if _is_ats(url): return True
    try:
        r = session.head(url, timeout=(2, 3), allow_redirects=True)
        if r.status_code < 400:
            return any(t in f"{r.url.lower()} {url.lower()}" for t in CAREER_TERMS)
    except requests.RequestException: pass
    try:
        r = session.get(url, timeout=(2, 4), allow_redirects=True, stream=True)
        ok = r.status_code < 400 and (any(t in f"{r.url.lower()} {url.lower()}" for t in CAREER_TERMS) or "text/html" in r.headers.get("content-type", "").lower())
        r.close(); return ok
    except requests.RequestException: return False


def _resolve_company_career(company: str) -> dict:
    """Resolve a company deterministically first, then use search only as fallback."""
    direct = resolve_company_domain(company)
    if direct.get("website"):
        print(f"[DISCOVERY] {company}: official domain -> {direct['website']}", flush=True)
        if direct.get("career_url"):
            return direct
        # The official domain is reliable even when /careers is not a simple path.
        return direct

    session = requests.Session(); session.headers.update(SEARCH_HEADERS)
    candidates: dict[str, tuple[int, str]] = {}
    links = _jina_results(session, company)
    if not links:
        for engine in ("https://www.google.com/search?q=", "https://www.bing.com/search?q=", "https://html.duckduckgo.com/html/?q="):
            try:
                r = session.get(engine + quote_plus(f'"{company}" careers jobs'), timeout=(2, 5), allow_redirects=True); r.raise_for_status()
                links = _search_html_links(r.text)
                if links: break
            except requests.RequestException: continue
    for url, title in links:
        score = _candidate_score(url, title, company)
        if score > 0 and (url not in candidates or score > candidates[url][0]): candidates[url] = (score, title)
    if not candidates: return {"website": None, "career_url": None, "status": "Not found"}
    for url, (score, _) in sorted(candidates.items(), key=lambda x: x[1][0], reverse=True)[:10]:
        if score >= 55 and _verify_candidate(session, url):
            return {"website": None if _is_ats(url) else f"{urlparse(url).scheme}://{urlparse(url).netloc}", "career_url": url, "status": "Found"}
    return {"website": None, "career_url": None, "status": "Low confidence"}


def load_career_urls(excel_path: str, discover: bool = True) -> list[str]:
    loader = CompanyLoader(); targets = loader.load_targets(excel_path)
    career_finder, website_finder = CareerFinder(), WebsiteFinder()
    urls, seen, results = [], set(), {}
    company_only = [t for t in targets if not t.get("career_url") and not t.get("website")]
    if company_only:
        print(f"[DISCOVERY] {len(company_only)} companies have no URL. Finding official domains/career pages automatically...", flush=True)
        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="career-discovery") as pool:
            futures = {pool.submit(_resolve_company_career, t["company"]): t["company"] for t in company_only}
            for completed, future in enumerate(as_completed(futures), 1):
                company = futures[future]
                try: result = future.result()
                except Exception as exc: result = {"website": None, "career_url": None, "status": f"Error: {type(exc).__name__}"}
                result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds"); results[company] = result
                print(f"[DISCOVERY] {completed}/{len(futures)} {company}: {result['status']} -> {result.get('career_url') or result.get('website') or '-'}", flush=True)
        loader.update_discovery_results(excel_path, results)
        print(f"[DISCOVERY] Excel updated: {excel_path}", flush=True)
    # Reload after enrichment so persisted URLs are used on this run too.
    targets = loader.load_targets(excel_path)
    for target in targets:
        company = target["company"]; career_url = target.get("career_url"); website = target.get("website")
        if career_url: candidates = [website_finder.normalize_url(career_url)]
        elif website: candidates = career_finder.find(website_finder.normalize_url(website), discover=discover)
        else: candidates = []
        for url in candidates:
            if url not in seen: seen.add(url); urls.append(url)
    return urls


def validate_startup(career_urls: list[str], settings: Settings) -> None:
    resume = Path(settings.resume_path)
    if not resume.is_file(): raise ValueError(f"Resume file not found: {resume}")
    if not career_urls: raise ValueError("No career URLs could be resolved from the supplied Excel file. Check the Discovery Status column in the workbook.")
    for url in career_urls:
        p = urlparse(str(url).strip())
        if p.scheme not in {"http", "https"} or not p.netloc: raise ValueError(f"Invalid career URL: {url}")
    Path(settings.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True); settings.notification_config()


def run_once(career_urls: list[str], settings: Settings) -> dict:
    scheduler = build_scheduler(settings)
    try: return scheduler.run_pipeline(career_urls=career_urls, resume_skills=load_resume_skills(settings), min_score=settings.min_match_score, notification=settings.notification_config(), preferences=settings.job_preferences())
    finally: scheduler.database.close()


def run_scheduled(career_urls: list[str], settings: Settings) -> None:
    scheduler = build_scheduler(settings); ProductionRunner(scheduler, career_urls, load_resume_skills(settings), settings).start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JobHunter AI job discovery pipeline")
    parser.add_argument("career_urls", nargs="*", help="Company career/ATS URLs to scan")
    parser.add_argument("--companies", help="Excel file containing Company Name, optionally Website/Career URL")
    parser.add_argument("--no-discovery", action="store_true", help="Skip homepage deep discovery when Website is supplied; company-name-only Excel still performs required career search")
    return parser.parse_args()


def main() -> int:
    args = parse_args(); settings = Settings.from_env()
    try:
        career_urls = list(args.career_urls)
        if args.companies: career_urls.extend(load_career_urls(args.companies, discover=not args.no_discovery))
        validate_startup(career_urls, settings)
        summary = run_once(career_urls, settings)
        print(f"JobHunter run complete: found={summary['jobs_found']} saved={summary['jobs_saved']} skipped={summary['jobs_skipped']} notifications={summary['notifications_sent']} errors={len(summary['errors'])}")
        return 0 if not summary["errors"] else 1
    except ValueError as exc:
        print(f"Configuration error: {exc}"); return 2


if __name__ == "__main__": raise SystemExit(main())
