import json
from types import SimpleNamespace
import pytest
from runner.production_runner import ProductionRunner

class Database:
    def __init__(self):self.closed=False
    def close(self):self.closed=True
class Scheduler:
    def __init__(self,summary=None,error=None):self.database=Database();self.summary=summary or {"jobs_found":1,"jobs_saved":1,"errors":[]};self.error=error;self.calls=[];self.shutdown_calls=[]
    def run_pipeline(self,**kwargs):
        self.calls.append(("run",kwargs))
        if self.error:raise self.error
        return self.summary
    def add_job(self,func,hours):self.calls.append(("add",func,hours))
    def start(self):self.calls.append(("start",))
    def shutdown(self,wait=True):self.shutdown_calls.append(wait)
class Settings:
    database_path="jobs.db";min_match_score=60;scheduler_hours=4;run_history_path=None;run_lock_path=None
    def notification_config(self):return {"channel":"telegram","minimum_priority":"high","minimum_recommendation_score":70}
    def job_preferences(self):return SimpleNamespace(target_titles=("QA",))

def make_runner(tmp_path,scheduler=None,settings=None):
    settings=settings or Settings();settings.run_history_path=str(tmp_path/"history.jsonl");settings.run_lock_path=str(tmp_path/"runner.lock")
    return ProductionRunner(scheduler or Scheduler(),["https://jobs.example.com"],["python","selenium"],settings)
def events(path):return [json.loads(line) for line in path.read_text().splitlines()]

def test_configured_paths_are_used(tmp_path):
    r=make_runner(tmp_path);assert r.history_path==tmp_path/"history.jsonl";assert r.lock_path==tmp_path/"runner.lock"
def test_lock_prevents_second_runner(tmp_path):
    first=make_runner(tmp_path);second=make_runner(tmp_path);assert first.acquire_lock() is True;assert second.acquire_lock() is False;first.release_lock();assert second.acquire_lock() is True;second.release_lock()
def test_release_lock_is_idempotent(tmp_path):
    r=make_runner(tmp_path);r.acquire_lock();r.release_lock();r.release_lock();assert not r.lock_path.exists()
def test_run_once_records_success_and_passes_configuration(tmp_path):
    s=Scheduler();r=make_runner(tmp_path,s);summary=r.run_once();assert summary["jobs_saved"]==1;kwargs=s.calls[0][1];assert kwargs["career_urls"]==r.career_urls;assert kwargs["resume_skills"]==r.resume_skills;assert kwargs["min_score"]==60;assert kwargs["notification"]["minimum_recommendation_score"]==70;assert kwargs["preferences"].target_titles==("QA",);rows=events(r.history_path);assert [x["event"] for x in rows]==["run_started","run_completed"];assert rows[-1]["summary"]["jobs_saved"]==1
def test_run_once_records_failure_and_reraises(tmp_path):
    r=make_runner(tmp_path,Scheduler(error=RuntimeError("network down")))
    with pytest.raises(RuntimeError,match="network down"):r.run_once()
    rows=events(r.history_path);assert [x["event"] for x in rows]==["run_started","run_failed"];assert rows[-1]["error"]=="network down"
def test_start_runs_immediately_schedules_and_cleans_up(tmp_path,monkeypatch):
    s=Scheduler();r=make_runner(tmp_path,s);monkeypatch.setattr("signal.signal",lambda *args:None);monkeypatch.setattr("signal.getsignal",lambda *args:None);r.start();assert s.calls[0][0]=="run";assert s.calls[1][0]=="add";assert s.calls[1][2]==4;assert s.calls[2]==("start",);assert s.database.closed is True;assert not r.lock_path.exists();assert [x["event"] for x in events(r.history_path)]==["runner_started","run_started","run_completed","runner_stopped"]
def test_start_cleans_up_when_initial_run_fails(tmp_path,monkeypatch):
    s=Scheduler(error=RuntimeError("boom"));r=make_runner(tmp_path,s);monkeypatch.setattr("signal.signal",lambda *args:None);monkeypatch.setattr("signal.getsignal",lambda *args:None)
    with pytest.raises(RuntimeError,match="boom"):r.start()
    assert s.database.closed is True;assert not r.lock_path.exists();assert events(r.history_path)[-1]["event"]=="runner_stopped"
def test_start_rejects_duplicate_instance(tmp_path):
    first=make_runner(tmp_path);second=make_runner(tmp_path);first.acquire_lock()
    try:
        with pytest.raises(RuntimeError,match="already active"):second.start()
    finally:first.release_lock()
def test_shutdown_is_safe_to_call_more_than_once(tmp_path):
    s=Scheduler();r=make_runner(tmp_path,s);r._shutdown();r._shutdown();assert s.shutdown_calls==[False]
