"""SQLite persistence for discovered, matched and tracked jobs."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path


class Database:
    """Store normalized jobs, match results and application progress."""
    MATCH_LIST_COLUMNS=("matched_skills","missing_skills","required_skills","preferred_skills","general_skills","matched_required_skills","missing_required_skills")
    APPLICATION_STATUSES=("new","viewed","applied","interview","rejected","offer")

    def __init__(self,db_path:str|Path="jobs.db"):
        self.db_path=str(db_path); self.conn=sqlite3.connect(self.db_path); self.conn.row_factory=sqlite3.Row; self._create_schema()
    def connect(self): return self.conn
    def execute(self,query,params=()):
        c=self.conn.cursor(); c.execute(query,params); self.conn.commit(); return c
    def fetchall(self,query,params=()):
        c=self.conn.cursor(); c.execute(query,params); return c.fetchall()

    def save_job(self,job,match=None):
        data=self._job_dict(job); apply_url=str(data.get("apply_url") or "").strip(); title=str(data.get("title") or "").strip(); company=str(data.get("company") or "").strip()
        if not apply_url: raise ValueError("Job apply_url is required")
        if not title: raise ValueError("Job title is required")
        if not company: raise ValueError("Job company is required")
        match=match or {}; score=float(match.get("score",0)); lists={n:list(match.get(n) or []) for n in self.MATCH_LIST_COLUMNS}
        c=self.execute("""INSERT INTO jobs(title,company,location,apply_url,description,platform,match_score,matched_skills,missing_skills,required_skills,preferred_skills,general_skills,matched_required_skills,missing_required_skills) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(apply_url) DO UPDATE SET title=excluded.title,company=excluded.company,location=excluded.location,description=excluded.description,platform=excluded.platform,match_score=excluded.match_score,matched_skills=excluded.matched_skills,missing_skills=excluded.missing_skills,required_skills=excluded.required_skills,preferred_skills=excluded.preferred_skills,general_skills=excluded.general_skills,matched_required_skills=excluded.matched_required_skills,missing_required_skills=excluded.missing_required_skills,updated_at=CURRENT_TIMESTAMP""",(title,company,str(data.get("location") or "").strip(),apply_url,str(data.get("description") or "").strip(),str(data.get("platform") or "unknown").strip().lower(),score,*(json.dumps(lists[n]) for n in self.MATCH_LIST_COLUMNS)))
        if c.lastrowid:return int(c.lastrowid)
        return int(self.conn.execute("SELECT id FROM jobs WHERE apply_url=?",(apply_url,)).fetchone()["id"])

    def save_jobs(self,jobs:Iterable,matches=None):
        matches=matches or {}; return [self.save_job(j,matches.get(str(self._job_dict(j).get("apply_url") or ""))) for j in jobs]

    def update_application_status(self,job_id,status):
        normalized=str(status or "").strip().lower()
        if normalized not in self.APPLICATION_STATUSES: raise ValueError(f"Invalid application status: {status}")
        if self.get_job(job_id) is None: raise KeyError(f"Job not found: {job_id}")
        self.execute("UPDATE jobs SET application_status=?,status_updated_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?",(normalized,int(job_id))); return self.get_job(job_id)

    def list_jobs(self,min_score=0.0,limit=100,status=None):
        params=[float(min_score)]; where="match_score >= ?"
        if status is not None:
            normalized=str(status).strip().lower()
            if normalized not in self.APPLICATION_STATUSES: raise ValueError(f"Invalid application status: {status}")
            where+=" AND application_status = ?"; params.append(normalized)
        params.append(int(limit)); rows=self.fetchall(f"SELECT * FROM jobs WHERE {where} ORDER BY match_score DESC,discovered_at DESC LIMIT ?",tuple(params)); return [self._row_to_dict(r) for r in rows]

    def get_analytics(self):
        """Return compact dashboard statistics in one database query."""
        row=self.conn.execute("""SELECT COUNT(*) AS total, COALESCE(ROUND(AVG(match_score),1),0) AS average_match_score, SUM(CASE WHEN application_status='new' THEN 1 ELSE 0 END) AS new, SUM(CASE WHEN application_status='viewed' THEN 1 ELSE 0 END) AS viewed, SUM(CASE WHEN application_status='applied' THEN 1 ELSE 0 END) AS applied, SUM(CASE WHEN application_status='interview' THEN 1 ELSE 0 END) AS interview, SUM(CASE WHEN application_status='rejected' THEN 1 ELSE 0 END) AS rejected, SUM(CASE WHEN application_status='offer' THEN 1 ELSE 0 END) AS offer FROM jobs""").fetchone()
        result=dict(row)
        for status in self.APPLICATION_STATUSES: result[status]=int(result.get(status) or 0)
        result["total"]=int(result["total"] or 0); result["average_match_score"]=float(result["average_match_score"] or 0)
        result["response_rate"]=round(((result["interview"]+result["offer"])/result["applied"]*100),1) if result["applied"] else 0.0
        return result

    def get_job(self,job_id):
        row=self.conn.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone(); return self._row_to_dict(row) if row else None
    def close(self): self.conn.close()

    def _create_schema(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,location TEXT NOT NULL DEFAULT '',apply_url TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unknown',match_score REAL NOT NULL DEFAULT 0,matched_skills TEXT NOT NULL DEFAULT '[]',missing_skills TEXT NOT NULL DEFAULT '[]',required_skills TEXT NOT NULL DEFAULT '[]',preferred_skills TEXT NOT NULL DEFAULT '[]',general_skills TEXT NOT NULL DEFAULT '[]',matched_required_skills TEXT NOT NULL DEFAULT '[]',missing_required_skills TEXT NOT NULL DEFAULT '[]',application_status TEXT NOT NULL DEFAULT 'new',status_updated_at TEXT,discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"""); self._migrate_schema()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs(application_status)"); self.conn.commit()

    def _migrate_schema(self):
        existing={r["name"] for r in self.conn.execute("PRAGMA table_info(jobs)").fetchall()}; migrations={"required_skills":"TEXT NOT NULL DEFAULT '[]'","preferred_skills":"TEXT NOT NULL DEFAULT '[]'","general_skills":"TEXT NOT NULL DEFAULT '[]'","matched_required_skills":"TEXT NOT NULL DEFAULT '[]'","missing_required_skills":"TEXT NOT NULL DEFAULT '[]'","application_status":"TEXT NOT NULL DEFAULT 'new'","status_updated_at":"TEXT"}
        for column,definition in migrations.items():
            if column not in existing:self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")

    @staticmethod
    def _job_dict(job):
        if isinstance(job,dict):return job
        if hasattr(job,"to_dict"):return job.to_dict()
        return {"title":getattr(job,"title",""),"company":getattr(job,"company",""),"location":getattr(job,"location",""),"apply_url":getattr(job,"apply_url",""),"description":getattr(job,"description",""),"platform":getattr(job,"platform","unknown")}
    @classmethod
    def _row_to_dict(cls,row):
        result=dict(row)
        for column in cls.MATCH_LIST_COLUMNS:result[column]=json.loads(result.get(column) or "[]")
        return result
