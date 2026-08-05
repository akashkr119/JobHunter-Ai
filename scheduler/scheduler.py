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
    ALERT_PRIORITIES={"apply_now":3,"high":2,"medium":1,"low":0}
    def __init__(self,scraper_factory:ScraperFactory|None=None,matcher:SkillMatcher|None=None,database:Database|None=None,notifier:Notifier|None=None)->None:
        self._scheduler=BlockingScheduler();self.scraper_factory=scraper_factory or ScraperFactory();self.matcher=matcher or SkillMatcher();self.database=database or Database();self.notifier=notifier
    def add_job(self,func,hours:int=1,**kwargs):
        if hours<=0:raise ValueError("hours must be greater than zero")
        return self._scheduler.add_job(func,trigger="interval",hours=hours,kwargs=kwargs or None)
    def add_pipeline_job(self,career_urls:Iterable[str],resume_skills:Iterable[str],hours:int=1,min_score:float=0.0,notification:dict|None=None):return self.add_job(self.run_pipeline,hours=hours,career_urls=tuple(career_urls),resume_skills=tuple(resume_skills),min_score=min_score,notification=notification)
    def run_pipeline(self,career_urls:Iterable[str],resume_skills:Iterable[str],min_score:float=0.0,company:str="",notification:dict|None=None)->dict:
        if not 0<=float(min_score)<=100:raise ValueError("min_score must be between 0 and 100")
        skills=tuple(resume_skills);summary={"sources":0,"jobs_found":0,"jobs_saved":0,"jobs_skipped":0,"jobs_expired":0,"notifications_sent":0,"notifications_suppressed":0,"errors":[]}
        for career_url in career_urls:
            summary["sources"]+=1
            try:jobs=self.scraper_factory.scrape(career_url,company=company)
            except Exception as exc:summary["errors"].append({"career_url":career_url,"stage":"scrape","error":str(exc)});continue
            summary["jobs_found"]+=len(jobs);seen_urls=[];platform=self._platform_for_source(career_url,jobs)
            for job in jobs:
                apply_url=str(getattr(job,"apply_url","") or "").strip()
                if apply_url:seen_urls.append(apply_url)
                match=self.matcher.match_job(skills,job)
                if match["score"]<float(min_score):summary["jobs_skipped"]+=1;continue
                existing=self._existing_job(job);job_id=self.database.save_job(job,match=match);summary["jobs_saved"]+=1;stored=self.database.get_job(job_id)
                if notification and self.notifier:
                    try:
                        should_notify=self._should_notify(stored,existing,notification)
                        if should_notify:self._notify(job,match,notification,stored);self.database.mark_job_notified(job_id,stored["priority_label"]);summary["notifications_sent"]+=1
                        else:summary["notifications_suppressed"]+=1
                    except Exception as exc:summary["errors"].append({"career_url":career_url,"stage":"notify","apply_url":apply_url,"error":str(exc)})
            if platform:
                try:summary["jobs_expired"]+=self.database.mark_missing_jobs_inactive(seen_urls,platform=platform)
                except Exception as exc:summary["errors"].append({"career_url":career_url,"stage":"lifecycle","error":str(exc)})
        return summary
    def _existing_job(self,job):
        d=self.database._job_dict(job);url=str(d.get("apply_url") or "").strip();key=self.database._job_key(d.get("title"),d.get("company"),d.get("location"));row=self.database.conn.execute("SELECT id FROM jobs WHERE apply_url=? OR (job_key=? AND job_key<>'') LIMIT 1",(url,key)).fetchone();return self.database.get_job(row["id"]) if row else None
    def _should_notify(self,job,previous,notification):
        if not job or not job.get("is_active",True) or job.get("application_status") not in ("new","viewed"):return False
        minimum=str(notification.get("minimum_priority","apply_now")).strip().lower()
        if minimum not in self.ALERT_PRIORITIES:raise ValueError("minimum_priority must be apply_now, high, medium or low")
        current=self.ALERT_PRIORITIES.get(job.get("priority_label"),0)
        if current<self.ALERT_PRIORITIES[minimum]:return False
        last=str(job.get("last_notified_priority") or "").strip().lower()
        if not last:return True
        return current>self.ALERT_PRIORITIES.get(last,-1)
    def _platform_for_source(self,career_url,jobs):
        for job in jobs:
            platform=str(getattr(job,"platform","") or "").strip().lower()
            if platform and platform!="unknown":return platform
        host=urlparse(str(career_url)).netloc.lower()
        if "greenhouse" in host:return "greenhouse"
        if "lever.co" in host:return "lever"
        if "myworkdayjobs" in host:return "workday"
        if "smartrecruiters" in host:return "smartrecruiters"
        return ""
    def _notify(self,job,match:dict,notification:dict,stored:dict|None=None)->dict:
        if not self.notifier:raise RuntimeError("Notifier is not configured")
        config=dict(notification);config.pop("minimum_priority",None);channel=config.pop("channel","");priority=(stored or {}).get("priority_label","high").replace("_"," ").title();message=self.notifier.format_job_alert(job,match,priority=priority,priority_score=(stored or {}).get("priority_score"))
        if str(channel).strip().lower()=="email":config.setdefault("subject",f"JobHunter {priority}: {match['score']:.0f}% match");config.setdefault("body",message)
        else:config.setdefault("message",message)
        return self.notifier.send(channel,**config)
    def start(self)->None:self._scheduler.start()
    def shutdown(self,wait:bool=True)->None:
        if self._scheduler.running:self._scheduler.shutdown(wait=wait)
class JobScheduler(Scheduler):pass
