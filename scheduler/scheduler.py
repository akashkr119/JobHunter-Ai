"""Scheduling and pipeline orchestration utilities for JobHunter AI."""

from collections.abc import Iterable
from urllib.parse import urlparse

from apscheduler.schedulers.blocking import BlockingScheduler

from crawler.scraper_factory import ScraperFactory
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from notifier.notifier import Notifier


class Scheduler:
    """Schedule and execute the JobHunter discovery pipeline."""

    def __init__(self, scraper_factory: ScraperFactory | None = None, matcher: SkillMatcher | None = None, database: Database | None = None, notifier: Notifier | None = None) -> None:
        self._scheduler = BlockingScheduler();self.scraper_factory=scraper_factory or ScraperFactory();self.matcher=matcher or SkillMatcher();self.database=database or Database();self.notifier=notifier

    def add_job(self,func,hours:int=1,**kwargs):
        if hours<=0:raise ValueError("hours must be greater than zero")
        return self._scheduler.add_job(func,trigger="interval",hours=hours,kwargs=kwargs or None)

    def add_pipeline_job(self,career_urls:Iterable[str],resume_skills:Iterable[str],hours:int=1,min_score:float=0.0,notification:dict|None=None):
        return self.add_job(self.run_pipeline,hours=hours,career_urls=tuple(career_urls),resume_skills=tuple(resume_skills),min_score=min_score,notification=notification)

    def run_pipeline(self,career_urls:Iterable[str],resume_skills:Iterable[str],min_score:float=0.0,company:str="",notification:dict|None=None)->dict:
        """Scrape, score, persist and expire jobs only after successful sources.

        Failed scrapes never mark existing jobs inactive. Lifecycle expiry is
        scoped to the detected ATS platform so one source cannot close jobs
        belonging to another platform.
        """
        if not 0<=float(min_score)<=100:raise ValueError("min_score must be between 0 and 100")
        skills=tuple(resume_skills);summary={"sources":0,"jobs_found":0,"jobs_saved":0,"jobs_skipped":0,"jobs_expired":0,"notifications_sent":0,"errors":[]}
        for career_url in career_urls:
            summary["sources"]+=1
            try:jobs=self.scraper_factory.scrape(career_url,company=company)
            except Exception as exc:
                summary["errors"].append({"career_url":career_url,"stage":"scrape","error":str(exc)});continue
            summary["jobs_found"]+=len(jobs);seen_urls=[];platform=self._platform_for_source(career_url,jobs)
            for job in jobs:
                apply_url=str(getattr(job,"apply_url","") or "").strip()
                if apply_url:seen_urls.append(apply_url)
                match=self.matcher.match_job(skills,job)
                if match["score"]<float(min_score):summary["jobs_skipped"]+=1;continue
                self.database.save_job(job,match=match);summary["jobs_saved"]+=1
                if notification and self.notifier:
                    try:self._notify(job,match,notification);summary["notifications_sent"]+=1
                    except Exception as exc:summary["errors"].append({"career_url":career_url,"stage":"notify","apply_url":apply_url,"error":str(exc)})
            # Only a completed scrape is authoritative enough to expire jobs.
            # Use all scraped URLs, including jobs below the score threshold.
            if platform:
                try:summary["jobs_expired"]+=self.database.mark_missing_jobs_inactive(seen_urls,platform=platform)
                except Exception as exc:summary["errors"].append({"career_url":career_url,"stage":"lifecycle","error":str(exc)})
        return summary

    def _platform_for_source(self,career_url,jobs):
        """Resolve a platform without making another network request."""
        for job in jobs:
            platform=str(getattr(job,"platform","") or "").strip().lower()
            if platform and platform!="unknown":return platform
        host=urlparse(str(career_url)).netloc.lower()
        if "greenhouse" in host:return "greenhouse"
        if "lever.co" in host:return "lever"
        if "myworkdayjobs" in host:return "workday"
        if "smartrecruiters" in host:return "smartrecruiters"
        return ""

    def _notify(self,job,match:dict,notification:dict)->dict:
        if not self.notifier:raise RuntimeError("Notifier is not configured")
        config=dict(notification);channel=config.pop("channel","");message=self.notifier.format_job_alert(job,match)
        if str(channel).strip().lower()=="email":config.setdefault("subject",f"JobHunter: {match['score']:.0f}% match");config.setdefault("body",message)
        else:config.setdefault("message",message)
        return self.notifier.send(channel,**config)

    def start(self)->None:self._scheduler.start()
    def shutdown(self,wait:bool=True)->None:
        if self._scheduler.running:self._scheduler.shutdown(wait=wait)

class JobScheduler(Scheduler):pass
