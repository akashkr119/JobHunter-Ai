"""Production lifecycle wrapper for scheduled JobHunter runs."""
from __future__ import annotations
import json
import logging
import os
import signal
import threading
from datetime import datetime,timezone
from pathlib import Path

class ProductionRunner:
    """Run the scheduled pipeline with locking, history and graceful shutdown."""
    def __init__(self,scheduler,career_urls,resume_skills,settings,history_path=None,lock_path=None):
        self.scheduler=scheduler;self.career_urls=tuple(career_urls);self.resume_skills=tuple(resume_skills);self.settings=settings
        base=Path(getattr(settings,"database_path","jobs.db")).resolve().parent
        configured_history=getattr(settings,"run_history_path",None);configured_lock=getattr(settings,"run_lock_path",None)
        self.history_path=Path(history_path or configured_history or base/"run_history.jsonl");self.lock_path=Path(lock_path or configured_lock or base/"jobhunter.lock");self._lock_fd=None;self._stopping=threading.Event();self.log=logging.getLogger("jobhunter.runner")
    def acquire_lock(self):
        self.lock_path.parent.mkdir(parents=True,exist_ok=True)
        try:self._lock_fd=os.open(self.lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(self._lock_fd,str(os.getpid()).encode());return True
        except FileExistsError:return False
    def release_lock(self):
        if self._lock_fd is not None:
            os.close(self._lock_fd);self._lock_fd=None
        try:self.lock_path.unlink()
        except FileNotFoundError:pass
    def record(self,event,**data):
        self.history_path.parent.mkdir(parents=True,exist_ok=True);row={"timestamp":datetime.now(timezone.utc).isoformat(),"event":event,**data}
        with self.history_path.open("a",encoding="utf-8") as f:f.write(json.dumps(row,default=str)+"\n")
        return row
    def run_once(self):
        started=datetime.now(timezone.utc);self.record("run_started",sources=len(self.career_urls))
        try:
            summary=self.scheduler.run_pipeline(career_urls=self.career_urls,resume_skills=self.resume_skills,min_score=self.settings.min_match_score,notification=self.settings.notification_config(),preferences=self.settings.job_preferences());self.record("run_completed",duration_seconds=round((datetime.now(timezone.utc)-started).total_seconds(),3),summary=summary);return summary
        except Exception as exc:self.record("run_failed",duration_seconds=round((datetime.now(timezone.utc)-started).total_seconds(),3),error=str(exc));raise
    def _shutdown(self,*_):
        if self._stopping.is_set():return
        self._stopping.set();self.log.info("Shutdown requested");self.scheduler.shutdown(wait=False)
    def start(self):
        if not self.acquire_lock():raise RuntimeError(f"JobHunter production runner is already active ({self.lock_path})")
        previous={}
        try:
            for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,self._shutdown)
            self.record("runner_started",interval_hours=self.settings.scheduler_hours,sources=len(self.career_urls));self.run_once();self.scheduler.add_job(self.run_once,hours=self.settings.scheduler_hours);self.scheduler.start()
        finally:
            self.record("runner_stopped");self.scheduler.database.close();self.release_lock()
            for sig,handler in previous.items():signal.signal(sig,handler)
