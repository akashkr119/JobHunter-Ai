"""SQLite persistence for discovered, matched and tracked jobs."""
import json,sqlite3
from collections.abc import Iterable
from pathlib import Path
class Database:
    MATCH_LIST_COLUMNS=("matched_skills","missing_skills","required_skills","preferred_skills","general_skills","matched_required_skills","missing_required_skills")
    APPLICATION_STATUSES=("new","viewed","applied","interview","rejected","offer")
    def __init__(self,db_path:str|Path="jobs.db"):
        self.db_path=str(db_path);self.conn=sqlite3.connect(self.db_path);self.conn.row_factory=sqlite3.Row;self._create_schema()
    def connect(self):return self.conn
    def execute(self,q,p=()):c=self.conn.cursor();c.execute(q,p);self.conn.commit();return c
    def fetchall(self,q,p=()):c=self.conn.cursor();c.execute(q,p);return c.fetchall()
    def save_job(self,job,match=None):
        d=self._job_dict(job);u=str(d.get("apply_url") or "").strip();t=str(d.get("title") or "").strip();co=str(d.get("company") or "").strip()
        if not u:raise ValueError("Job apply_url is required")
        if not t:raise ValueError("Job title is required")
        if not co:raise ValueError("Job company is required")
        match=match or {};lists={n:list(match.get(n) or []) for n in self.MATCH_LIST_COLUMNS};c=self.execute("""INSERT INTO jobs(title,company,location,apply_url,description,platform,match_score,matched_skills,missing_skills,required_skills,preferred_skills,general_skills,matched_required_skills,missing_required_skills,last_seen_at,is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,1) ON CONFLICT(apply_url) DO UPDATE SET title=excluded.title,company=excluded.company,location=excluded.location,description=excluded.description,platform=excluded.platform,match_score=excluded.match_score,matched_skills=excluded.matched_skills,missing_skills=excluded.missing_skills,required_skills=excluded.required_skills,preferred_skills=excluded.preferred_skills,general_skills=excluded.general_skills,matched_required_skills=excluded.matched_required_skills,missing_required_skills=excluded.missing_required_skills,last_seen_at=CURRENT_TIMESTAMP,is_active=1,updated_at=CURRENT_TIMESTAMP""",(t,co,str(d.get("location") or "").strip(),u,str(d.get("description") or "").strip(),str(d.get("platform") or "unknown").strip().lower(),float(match.get("score",0)),*(json.dumps(lists[n]) for n in self.MATCH_LIST_COLUMNS)))
        if c.lastrowid:return int(c.lastrowid)
        return int(self.conn.execute("SELECT id FROM jobs WHERE apply_url=?",(u,)).fetchone()["id"])
    def save_jobs(self,jobs:Iterable,matches=None):
        matches=matches or {};return [self.save_job(j,matches.get(str(self._job_dict(j).get("apply_url") or ""))) for j in jobs]
    def mark_missing_jobs_inactive(self,seen_apply_urls,platform=None):
        """Mark jobs not seen in a successful scrape inactive while preserving history."""
        urls={str(u).strip() for u in (seen_apply_urls or []) if str(u).strip()};where="is_active=1";params=[]
        if platform is not None:where+=" AND platform=?";params.append(str(platform).strip().lower())
        if urls:
            marks=','.join('?' for _ in urls);where+=f" AND apply_url NOT IN ({marks})";params.extend(sorted(urls))
        c=self.execute(f"UPDATE jobs SET is_active=0,updated_at=CURRENT_TIMESTAMP WHERE {where}",tuple(params));return c.rowcount
    def update_application_status(self,job_id,status):
        s=str(status or "").strip().lower()
        if s not in self.APPLICATION_STATUSES:raise ValueError(f"Invalid application status: {status}")
        self._require_job(job_id);self.execute("UPDATE jobs SET application_status=?,status_updated_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?",(s,int(job_id)));return self.get_job(job_id)
    def update_job_tracking(self,job_id,saved=None,notes=None):
        self._require_job(job_id);sets=[];params=[]
        if saved is not None:sets.append("is_saved=?");params.append(1 if bool(saved) else 0)
        if notes is not None:
            notes=str(notes)
            if len(notes)>5000:raise ValueError("notes must be 5000 characters or fewer")
            sets.append("notes=?");params.append(notes)
        if not sets:raise ValueError("saved or notes is required")
        sets.append("updated_at=CURRENT_TIMESTAMP");params.append(int(job_id));self.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?",tuple(params));return self.get_job(job_id)
    def list_jobs(self,min_score=0.0,limit=100,status=None,saved=None,active=None):
        params=[float(min_score)];where="match_score >= ?"
        if status is not None:
            s=str(status).strip().lower()
            if s not in self.APPLICATION_STATUSES:raise ValueError(f"Invalid application status: {status}")
            where+=" AND application_status=?";params.append(s)
        if saved is not None:where+=" AND is_saved=?";params.append(1 if saved else 0)
        if active is not None:where+=" AND is_active=?";params.append(1 if active else 0)
        params.append(int(limit));return [self._row_to_dict(r) for r in self.fetchall(f"SELECT * FROM jobs WHERE {where} ORDER BY is_active DESC,match_score DESC,discovered_at DESC LIMIT ?",tuple(params))]
    def get_analytics(self):
        r=dict(self.conn.execute("""SELECT COUNT(*) total,SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) active,SUM(CASE WHEN is_active=0 THEN 1 ELSE 0 END) inactive,SUM(CASE WHEN date(discovered_at)=date('now') THEN 1 ELSE 0 END) new_today,COALESCE(ROUND(AVG(CASE WHEN is_active=1 THEN match_score END),1),0) average_match_score,SUM(CASE WHEN is_saved=1 THEN 1 ELSE 0 END) saved,SUM(CASE WHEN application_status='new' THEN 1 ELSE 0 END) new,SUM(CASE WHEN application_status='viewed' THEN 1 ELSE 0 END) viewed,SUM(CASE WHEN application_status='applied' THEN 1 ELSE 0 END) applied,SUM(CASE WHEN application_status='interview' THEN 1 ELSE 0 END) interview,SUM(CASE WHEN application_status='rejected' THEN 1 ELSE 0 END) rejected,SUM(CASE WHEN application_status='offer' THEN 1 ELSE 0 END) offer FROM jobs""").fetchone());r["total"]=int(r["total"] or 0);r["active"]=int(r["active"] or 0);r["inactive"]=int(r["inactive"] or 0);r["new_today"]=int(r["new_today"] or 0);r["saved"]=int(r["saved"] or 0);r["average_match_score"]=float(r["average_match_score"] or 0)
        for s in self.APPLICATION_STATUSES:r[s]=int(r.get(s) or 0)
        r["response_rate"]=round((r["interview"]+r["offer"])/r["applied"]*100,1) if r["applied"] else 0.0;return r
    def get_job(self,job_id):
        row=self.conn.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone();return self._row_to_dict(row) if row else None
    def _require_job(self,job_id):
        if self.get_job(job_id) is None:raise KeyError(f"Job not found: {job_id}")
    def close(self):self.conn.close()
    def _create_schema(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,location TEXT NOT NULL DEFAULT '',apply_url TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unknown',match_score REAL NOT NULL DEFAULT 0,matched_skills TEXT NOT NULL DEFAULT '[]',missing_skills TEXT NOT NULL DEFAULT '[]',required_skills TEXT NOT NULL DEFAULT '[]',preferred_skills TEXT NOT NULL DEFAULT '[]',general_skills TEXT NOT NULL DEFAULT '[]',matched_required_skills TEXT NOT NULL DEFAULT '[]',missing_required_skills TEXT NOT NULL DEFAULT '[]',application_status TEXT NOT NULL DEFAULT 'new',status_updated_at TEXT,is_saved INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '',is_active INTEGER NOT NULL DEFAULT 1,last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""");self._migrate_schema();self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs(application_status)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_saved ON jobs(is_saved)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active)");self.conn.commit()
    def _migrate_schema(self):
        e={r["name"] for r in self.conn.execute("PRAGMA table_info(jobs)").fetchall()};m={"required_skills":"TEXT NOT NULL DEFAULT '[]'","preferred_skills":"TEXT NOT NULL DEFAULT '[]'","general_skills":"TEXT NOT NULL DEFAULT '[]'","matched_required_skills":"TEXT NOT NULL DEFAULT '[]'","missing_required_skills":"TEXT NOT NULL DEFAULT '[]'","application_status":"TEXT NOT NULL DEFAULT 'new'","status_updated_at":"TEXT","is_saved":"INTEGER NOT NULL DEFAULT 0","notes":"TEXT NOT NULL DEFAULT ''","is_active":"INTEGER NOT NULL DEFAULT 1","last_seen_at":"TEXT"}
        for c,d in m.items():
            if c not in e:self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {c} {d}")
        self.conn.execute("UPDATE jobs SET last_seen_at=COALESCE(last_seen_at,updated_at,discovered_at,CURRENT_TIMESTAMP)")
    @staticmethod
    def _job_dict(j):
        if isinstance(j,dict):return j
        if hasattr(j,"to_dict"):return j.to_dict()
        return {"title":getattr(j,"title",""),"company":getattr(j,"company",""),"location":getattr(j,"location",""),"apply_url":getattr(j,"apply_url",""),"description":getattr(j,"description",""),"platform":getattr(j,"platform","unknown")}
    @classmethod
    def _row_to_dict(cls,row):
        r=dict(row)
        for c in cls.MATCH_LIST_COLUMNS:r[c]=json.loads(r.get(c) or "[]")
        r["is_saved"]=bool(r.get("is_saved",0));r["is_active"]=bool(r.get("is_active",1));return r
