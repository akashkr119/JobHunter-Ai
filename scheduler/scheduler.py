"""Scheduling and pipeline orchestration utilities for JobHunter AI."""
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import urlparse
from apscheduler.schedulers.blocking import BlockingScheduler
from crawler.scraper_factory import ScraperFactory
from database.db import Database
from matcher.skill_matcher import SkillMatcher
from matcher.job_preferences import JobPreferences
from matcher.recommendation_ranker import RecommendationRanker
from notifier.notifier import Notifier
class Scheduler:
    """Schedule and execute the JobHunter discovery pipeline."""
    ALERT_PRIORITIES={"apply_now":3,"high":2,"medium":1,"low":0}
    MAX_SCRAPE_WORKERS=8
    def __init__(self,scraper_factory:ScraperFactory|None=None,matcher:SkillMatcher|None=None,database:Database|None=None,notifier:Notifier|None=None)->None:
        self._scheduler=BlockingScheduler();self.scraper_factory=scraper_factory or ScraperFactory();self.matcher=matcher or SkillMatcher();self.database=database or Database();self.notifier=notifier
    def add_job(self,func,hours:int=1,**kwargs):
        if hours<=0:raise ValueError("hours must be greater than zero")
        return self._scheduler.add_job(func,trigger="interval",hours=hours,kwargs=kwargs or None)
    def add_pipeline_job(self,career_urls:Iterable[str],resume_skills:Iterable[str],hours:int=1,min_score:float=0.0,notification:dict|None=None,preferences:JobPreferences|dict|None=None):return self.add_job(self.run_pipeline,hours=hours,career_urls=tuple(career_urls),resume_skills=tuple(resume_skills),min_score=min_score,notification=notification,preferences=preferences)
    def _scrape_one(self,career_url:str)->tuple[str,list,Exception|None]:
        try:return career_url,self.scraper_factory.scrape(career_url),None
        except Exception as exc:return career_url,[],exc
    def run_pipeline(self,career_urls:Iterable[str],resume_skills:Iterable[str],min_score:float=0.0,company:str="",notification:dict|None=None,preferences:JobPreferences|dict|None=None)->dict:
        if not 0<=float(min_score)<=100:raise ValueError("min_score must be between 0 and 100")
        prefs=preferences if isinstance(preferences,JobPreferences) else JobPreferences.from_dict(preferences);skills=tuple(resume_skills);summary={"sources":0,"jobs_found":0,"jobs_saved":0,"jobs_skipped":0,"jobs_preference_excluded":0,"jobs_expired":0,"notifications_sent":0,"notifications_suppressed":0,"errors":[]}
        urls=tuple(career_urls);summary["sources"]=len(urls)
        scraped=[]
        with ThreadPoolExecutor(max_workers=min(self.MAX_SCRAPE_WORKERS,max(1,len(urls))),thread_name_prefix="job-scraper") as pool:
            futures=[pool.submit(self._scrape_one,url) for url in urls]
            for future in as_completed(futures):scraped.append(future.result())
        scraped_by_url={url:(jobs,error) for url,jobs,error in scraped}
        for career_url in urls:
            jobs,error=scraped_by_url.get(career_url,([],RuntimeError("scrape result missing")))
            if error is not None:summary["errors"].append({"career_url":career_url,"stage":"scrape","error":str(error)});continue
            summary["jobs_found"]+=len(jobs);seen_urls=[];platform=self._platform_for_source(career_url,jobs)
            for job in jobs:
                apply_url=str(getattr(job,"apply_url","") or "").strip()
                if apply_url:seen_urls.append(apply_url)
                preference=prefs.evaluate(job)
                if preference["excluded_keywords"]:
                    summary["jobs_preference_excluded"]+=1;summary["jobs_skipped"]+=1;self._diagnose_skip(job,"preference",preference.get("excluded_keywords"),None,min_score);continue
                match=self.matcher.match_job(skills,job);match["preference_score"]=preference["preference_score"];match["preference_match"]=preference["preference_match"];match["preference_details"]=preference
                if match["score"]<float(min_score):
                    summary["jobs_skipped"]+=1;self._diagnose_skip(job,"score",None,match,min_score);continue
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
    @staticmethod
    def _diagnose_skip(job,reason,excluded,match,min_score):
        """Print concise rejection diagnostics so zero-save runs are actionable."""
        title=str(getattr(job,"title","") or "Untitled").strip();company=str(getattr(job,"company","") or "Unknown company").strip()
        if reason=="preference":
            print(f"[MATCH] SKIP preference | {company} | {title} | excluded={list(excluded or [])}",flush=True);return
        match=match or {};score=float(match.get("score",0.0));matched=match.get("matched_skills",[]);missing=match.get("missing_skills",[]);required=match.get("missing_required_skills",[])
        print(f"[MATCH] SKIP score | {company} | {title} | score={score:.1f}/{float(min_score):.1f} | matched={matched} | missing={missing} | missing_required={required}",flush=True)
    def _existing_job(self,job):
        d=self.database._job_dict(job);url=str(d.get("apply_url") or "").strip();key=self.database._job_key(d.get("title"),d.get("company"),d.get("location"));row=self.database.conn.execute("SELECT id FROM jobs WHERE apply_url=? OR (job_key=? AND job_key<>'') LIMIT 1",(url,key)).fetchone();return self.database.get_job(row["id"]) if row else None
    def _should_notify(self,job,previous,notification):
        if not job or not job.get("is_active",True) or job.get("application_status") not in ("new","viewed"):return False
        minimum_score=notification.get("minimum_recommendation_score")
        if minimum_score is not None:
            try:minimum_score=float(minimum_score)
            except (TypeError,ValueError):raise ValueError("minimum_recommendation_score must be between 0 and 100")
            if not 0<=minimum_score<=100:raise ValueError("minimum_recommendation_score must be between 0 and 100")
            if RecommendationRanker.score(job)["recommendation_score"]<minimum_score:return False
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
        config=dict(notification);config.pop("minimum_priority",None);config.pop("minimum_recommendation_score",None);channel=config.pop("channel","");priority=(stored or {}).get("priority_label","high").replace("_"," ").title();recommendation=RecommendationRanker.score(stored or {"match_score":match.get("score",0),"preference_score":match.get("preference_score",100)});message=self.notifier.format_job_alert(job,match,priority=priority,priority_score=(stored or {}).get("priority_score"));message=f"{message}\nRecommendation: {recommendation['recommendation_score']:.1f}/100 ({recommendation['recommendation_label'].replace('_',' ').title()})"
        if str(channel).strip().lower()=="email":config.setdefault("subject",f"JobHunter {recommendation['recommendation_label'].replace('_',' ').title()}: {recommendation['recommendation_score']:.0f}% recommendation");config.setdefault("body",message)
        else:config.setdefault("message",message)
        return self.notifier.send(channel,**config)
    def start(self)->None:self._scheduler.start()
    def shutdown(self,wait:bool=True)->None:
        if self._scheduler.running:self._scheduler.shutdown(wait=wait)
class JobScheduler(Scheduler):pass
