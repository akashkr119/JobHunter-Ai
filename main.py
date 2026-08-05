"""Command-line entry point for JobHunter AI."""

import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

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


def build_scheduler(settings: Settings) -> Scheduler:
    """Build application services from centralized settings."""
    notifier = None
    if settings.notification_channel:
        notifier = Notifier(smtp_host=settings.smtp_host,smtp_port=settings.smtp_port,smtp_username=settings.smtp_username,smtp_password=settings.smtp_password,smtp_sender=settings.smtp_sender,telegram_bot_token=settings.telegram_bot_token)
    return Scheduler(matcher=SkillMatcher(),database=Database(settings.database_path),notifier=notifier)


def load_resume_skills(settings: Settings) -> list[str]:
    """Parse the configured resume and return detected skills."""
    return ResumeParser().parse(settings.resume_path)["skills"]


def load_career_urls(excel_path: str, discover: bool = True) -> list[str]:
    """Resolve career URLs from structured company Excel input."""
    targets=CompanyLoader().load_targets(excel_path);career_finder=CareerFinder();website_finder=WebsiteFinder();urls=[];seen=set()
    for target in targets:
        career_url=target.get("career_url")
        if career_url:candidates=[website_finder.normalize_url(career_url)]
        elif target.get("website"):candidates=career_finder.find(website_finder.find(target["company"],target["website"]),discover=discover)
        else:continue
        for url in candidates:
            if url not in seen:seen.add(url);urls.append(url)
    return urls


def validate_startup(career_urls:list[str],settings:Settings)->None:
    """Fail fast on unsafe or incomplete runtime configuration."""
    resume=Path(settings.resume_path)
    if not resume.is_file():raise ValueError(f"Resume file not found: {resume}")
    if not career_urls:raise ValueError("Provide at least one career URL or --companies Excel file")
    for url in career_urls:
        parsed=urlparse(str(url).strip())
        if parsed.scheme not in {"http","https"} or not parsed.netloc:raise ValueError(f"Invalid career URL: {url}")
    Path(settings.database_path).expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
    if settings.run_history_path:Path(settings.run_history_path).expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
    if settings.run_lock_path:Path(settings.run_lock_path).expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
    settings.notification_config()


def run_once(career_urls:list[str],settings:Settings)->dict:
    """Execute one complete discovery run."""
    scheduler=build_scheduler(settings)
    try:return scheduler.run_pipeline(career_urls=career_urls,resume_skills=load_resume_skills(settings),min_score=settings.min_match_score,notification=settings.notification_config(),preferences=settings.job_preferences())
    finally:scheduler.database.close()


def run_scheduled(career_urls:list[str],settings:Settings)->None:
    """Run continuously with production lifecycle safeguards."""
    scheduler=build_scheduler(settings);runner=ProductionRunner(scheduler,career_urls,load_resume_skills(settings),settings);runner.start()


def parse_args()->argparse.Namespace:
    parser=argparse.ArgumentParser(description="JobHunter AI job discovery pipeline");parser.add_argument("career_urls",nargs="*",help="Company career/ATS URLs to scan");parser.add_argument("--companies",help="Excel file containing Company, Website and/or Career URL columns");parser.add_argument("--no-discovery",action="store_true",help="Do not fetch company homepages; use common career URL candidates only");parser.add_argument("--scheduled",action="store_true",help="Run continuously using the production runner and JOBHUNTER_SCHEDULER_HOURS");parser.add_argument("--env-file",default=None,help="Optional path to a .env configuration file");return parser.parse_args()


def main()->int:
    args=parse_args()
    try:
        settings=Settings.from_env(args.env_file);logging.basicConfig(level=getattr(logging,str(getattr(settings,"log_level","INFO")).upper(),logging.INFO),format="%(asctime)s %(levelname)s %(name)s %(message)s");career_urls=list(args.career_urls)
        if args.companies:career_urls.extend(load_career_urls(args.companies,discover=not args.no_discovery))
        career_urls=list(dict.fromkeys(career_urls));validate_startup(career_urls,settings)
        if args.scheduled:run_scheduled(career_urls,settings);return 0
        summary=run_once(career_urls,settings);print("JobHunter run complete: "f"found={summary['jobs_found']} "f"saved={summary['jobs_saved']} "f"skipped={summary['jobs_skipped']} "f"notifications={summary['notifications_sent']} "f"errors={len(summary['errors'])}");return 0 if not summary["errors"] else 1
    except (ValueError,FileNotFoundError) as exc:raise SystemExit(f"Configuration error: {exc}") from exc


if __name__=="__main__":raise SystemExit(main())
