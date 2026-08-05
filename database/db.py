"""SQLite persistence for discovered, matched and tracked jobs."""
import json,re,sqlite3
from collections.abc import Iterable
from datetime import datetime,timezone,timedelta
from pathlib import Path
class Database:
    MATCH_LIST_COLUMNS=("matched_skills","missing_skills","required_skills","preferred_skills","general_skills","matched_required_skills","missing_required_skills")
    APPLICATION_STATUSES=("new","viewed","applied","interview","rejected","offer")
    def __init__(self,db_path:str|Path="jobs.db"):self.db_path=str(db_path);self.conn=sqlite3.connect(self.db_path);self.conn.row_factory=sqlite3.Row;self._create_schema()
    def connect(self):return self.conn
    def execute(self,q,p=()):c=self.conn.cursor();c.execute(q,p);self.conn.commit();return c
    def fetchall(self,q,p=()):c=self.conn.cursor();c.execute(q,p);return c.fetchall()
    @staticmethod
    def _identity_text(value):return re.sub(r"[^a-z0-9]+"," ",str(value or "").lower()).strip()
    @classmethod
    def _job_key(cls,title,company,location=""):return "|".join((cls._identity_text(company),cls._identity_text(title),cls._identity_text(location)))
    @staticmethod
    def _age_days(value):
        if not value:return 365.0
        try:dt=datetime.fromisoformat(str(value).replace("Z","+00:00"));dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc);return max(0.0,(datetime.now(timezone.utc)-dt).total_seconds()/86400)
        except (TypeError,ValueError):return 365.0
    @classmethod
    def _priority(cls,row):
        match=max(0.0,min(100.0,float(row.get("match_score") or 0)));age=cls._age_days(row.get("last_seen_at") or row.get("discovered_at"));freshness=max(0.0,100.0-min(age,30.0)/30.0*100.0);status=str(row.get("application_status") or "new").lower();state={"new":100,"viewed":85,"applied":35,"interview":15,"offer":5,"rejected":0}.get(status,50);active=100 if row.get("is_active",True) else 0;return round(max(0.0,min(100.0,match*.60+freshness*.20+state*.10+active*.10)),1)
    @classmethod
    def _priority_label(cls,score):
        if score>=80:return "apply_now"
        if score>=65:return "high"
        if score>=45:return "medium"
        return "low"
    @staticmethod
    def _follow_up(row):
        status=str(row.get("application_status") or "new").lower();applied=row.get("applied_at");days=max(1,int(row.get("follow_up_days") or 7));done=bool(row.get("follow_up_completed",0))
        if status!="applied" or not applied or done:return {"follow_up_status":"none","follow_up_due_at":None,"follow_up_days_remaining":None}
        try:dt=datetime.fromisoformat(str(applied).replace("Z","+00:00"));dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc);due=dt+timedelta(days=days);remaining=(due-datetime.now(timezone.utc)).total_seconds()/86400
        except (TypeError,ValueError):return {"follow_up_status":"none","follow_up_due_at":None,"follow_up_days_remaining":None}
        state="overdue" if remaining<0 else ("due_soon" if remaining<=2 else "scheduled");return {"follow_up_status":state,"follow_up_due_at":due.isoformat(),"follow_up_days_remaining":max(0,int(remaining+0.999))}
    def save_job(self,job,match=None):
        d=self._job_dict(job);u=str(d.get("apply_url") or "").strip();t=str(d.get("title") or "").strip();co=str(d.get("company") or "").strip();loc=str(d.get("location") or "").strip();platform=str(d.get("platform") or "unknown").strip().lower();key=self._job_key(t,co,loc)
        if not u:raise ValueError("Job apply_url is required")
        if not t:raise ValueError("Job title is required")
        if not co:raise ValueError("Job company is required")
        match=match or {};lists={n:list(match.get(n) or []) for n in self.MATCH_LIST_COLUMNS};values=(t,co,loc,u,platform,float(match.get("score",0)),str(d.get("description") or "").strip(),key,*(json.dumps(lists[n]) for n in self.MATCH_LIST_COLUMNS));existing=self.conn.execute("SELECT id,apply_url FROM jobs WHERE apply_url=? OR (job_key=? AND job_key<>'') ORDER BY CASE WHEN apply_url=? THEN 0 ELSE 1 END,id LIMIT 1",(u,key,u)).fetchone()
        if existing:
            aliases={r["apply_url"] for r in self.conn.execute("SELECT apply_url FROM job_aliases WHERE job_id=?",(existing["id"],)).fetchall()};aliases.update((existing["apply_url"],u));self.execute("""UPDATE jobs SET title=?,company=?,location=?,apply_url=?,platform=?,match_score=?,description=?,job_key=?,matched_skills=?,missing_skills=?,required_skills=?,preferred_skills=?,general_skills=?,matched_required_skills=?,missing_required_skills=?,last_seen_at=CURRENT_TIMESTAMP,is_active=1,updated_at=CURRENT_TIMESTAMP WHERE id=?""",(*values,int(existing["id"])))
            for alias in aliases:self.execute("INSERT OR IGNORE INTO job_aliases(job_id,apply_url) VALUES(?,?)",(int(existing["id"]),alias))
            return int(existing["id"])
        c=self.execute("""INSERT INTO jobs(title,company,location,apply_url,platform,match_score,description,job_key,matched_skills,missing_skills,required_skills,preferred_skills,general_skills,matched_required_skills,missing_required_skills,last_seen_at,is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,1)""",values);job_id=int(c.lastrowid);self.execute("INSERT OR IGNORE INTO job_aliases(job_id,apply_url) VALUES(?,?)",(job_id,u));return job_id
    def save_jobs(self,jobs:Iterable,matches=None):matches=matches or {};return [self.save_job(j,matches.get(str(self._job_dict(j).get("apply_url") or ""))) for j in jobs]
    def mark_job_notified(self,job_id,priority_label):self._require_job(job_id);self.execute("UPDATE jobs SET last_notified_at=CURRENT_TIMESTAMP,last_notified_priority=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(str(priority_label or "").strip().lower(),int(job_id)));return self.get_job(job_id)
    def mark_missing_jobs_inactive(self,seen_apply_urls,platform=None):
        urls={str(u).strip() for u in (seen_apply_urls or []) if str(u).strip()};where="is_active=1";params=[]
        if platform is not None:where+=" AND platform=?";params.append(str(platform).strip().lower())
        if urls:marks=','.join('?' for _ in urls);where+=f" AND id NOT IN (SELECT job_id FROM job_aliases WHERE apply_url IN ({marks}))";params.extend(sorted(urls))
        return self.execute(f"UPDATE jobs SET is_active=0,updated_at=CURRENT_TIMESTAMP WHERE {where}",tuple(params)).rowcount
    def update_application_status(self,job_id,status):
        s=str(status or "").strip().lower()
        if s not in self.APPLICATION_STATUSES:raise ValueError(f"Invalid application status: {status}")
        self._require_job(job_id)
        if s=="applied":self.execute("UPDATE jobs SET application_status=?,status_updated_at=CURRENT_TIMESTAMP,applied_at=COALESCE(applied_at,CURRENT_TIMESTAMP),follow_up_completed=0,updated_at=CURRENT_TIMESTAMP WHERE id=?",(s,int(job_id)))
        else:self.execute("UPDATE jobs SET application_status=?,status_updated_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?",(s,int(job_id)))
        return self.get_job(job_id)
    def update_follow_up(self,job_id,days=None,completed=None):
        job=self.get_job(job_id)
        if job is None:raise KeyError(f"Job not found: {job_id}")
        sets=[];params=[]
        if days is not None:
            days=int(days)
            if not 1<=days<=90:raise ValueError("follow_up_days must be between 1 and 90")
            sets.append("follow_up_days=?");params.append(days)
        if completed is not None:
            if not isinstance(completed,bool):raise ValueError("completed must be a boolean")
            sets.append("follow_up_completed=?");params.append(1 if completed else 0)
        if not sets:raise ValueError("follow_up_days or completed is required")
        sets.append("updated_at=CURRENT_TIMESTAMP");params.append(int(job_id));self.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?",tuple(params));return self.get_job(job_id)
    def update_job_tracking(self,job_id,saved=None,notes=None):
        self._require_job(job_id);sets=[];params=[]
        if saved is not None:sets.append("is_saved=?");params.append(1 if bool(saved) else 0)
        if notes is not None:
            notes=str(notes)
            if len(notes)>5000:raise ValueError("notes must be 5000 characters or fewer")
            sets.append("notes=?");params.append(notes)
        if not sets:raise ValueError("saved or notes is required")
        sets.append("updated_at=CURRENT_TIMESTAMP");params.append(int(job_id));self.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?",tuple(params));return self.get_job(job_id)
    def list_jobs(self,min_score=0.0,limit=100,status=None,saved=None,active=None,follow_up=None):
        params=[float(min_score)];where="match_score >= ?"
        if status is not None:
            s=str(status).strip().lower()
            if s not in self.APPLICATION_STATUSES:raise ValueError(f"Invalid application status: {status}")
            where+=" AND application_status=?";params.append(s)
        if saved is not None:where+=" AND is_saved=?";params.append(1 if saved else 0)
        if active is not None:where+=" AND is_active=?";params.append(1 if active else 0)
        rows=[self._row_to_dict(r) for r in self.fetchall(f"SELECT * FROM jobs WHERE {where}",tuple(params))]
        if follow_up is not None:
            allowed={"scheduled","due_soon","overdue","none"}
            if follow_up not in allowed:raise ValueError("follow_up must be scheduled, due_soon, overdue or none")
            rows=[r for r in rows if r["follow_up_status"]==follow_up]
        rows.sort(key=lambda r:(r["priority_score"],r["match_score"]),reverse=True);return rows[:int(limit)]
    def get_analytics(self):
        r=dict(self.conn.execute("""SELECT COUNT(*) total,SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) active,SUM(CASE WHEN is_active=0 THEN 1 ELSE 0 END) inactive,SUM(CASE WHEN date(discovered_at)=date('now') THEN 1 ELSE 0 END) new_today,COALESCE(ROUND(AVG(CASE WHEN is_active=1 THEN match_score END),1),0) average_match_score,SUM(CASE WHEN is_saved=1 THEN 1 ELSE 0 END) saved,SUM(CASE WHEN application_status='new' THEN 1 ELSE 0 END) new,SUM(CASE WHEN application_status='viewed' THEN 1 ELSE 0 END) viewed,SUM(CASE WHEN application_status='applied' THEN 1 ELSE 0 END) applied,SUM(CASE WHEN application_status='interview' THEN 1 ELSE 0 END) interview,SUM(CASE WHEN application_status='rejected' THEN 1 ELSE 0 END) rejected,SUM(CASE WHEN application_status='offer' THEN 1 ELSE 0 END) offer FROM jobs""").fetchone());r={k:(int(v or 0) if k!="average_match_score" else float(v or 0)) for k,v in r.items()}
        for s in self.APPLICATION_STATUSES:r[s]=int(r.get(s) or 0)
        follow=[self._row_to_dict(x) for x in self.fetchall("SELECT * FROM jobs WHERE application_status='applied' AND follow_up_completed=0")];r["follow_up_due"]=sum(1 for x in follow if x["follow_up_status"] in ("due_soon","overdue"));r["response_rate"]=round((r["interview"]+r["offer"])/r["applied"]*100,1) if r["applied"] else 0.0;return r
    def get_job(self,job_id):
        row=self.conn.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
        if not row:return None
        result=self._row_to_dict(row);result["source_urls"]=[r["apply_url"] for r in self.conn.execute("SELECT apply_url FROM job_aliases WHERE job_id=? ORDER BY id",(job_id,)).fetchall()];return result
    def _require_job(self,job_id):
        if self.get_job(job_id) is None:raise KeyError(f"Job not found: {job_id}")
    def close(self):self.conn.close()
    def _create_schema(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,location TEXT NOT NULL DEFAULT '',apply_url TEXT NOT NULL UNIQUE,description TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unknown',job_key TEXT NOT NULL DEFAULT '',match_score REAL NOT NULL DEFAULT 0,matched_skills TEXT NOT NULL DEFAULT '[]',missing_skills TEXT NOT NULL DEFAULT '[]',required_skills TEXT NOT NULL DEFAULT '[]',preferred_skills TEXT NOT NULL DEFAULT '[]',general_skills TEXT NOT NULL DEFAULT '[]',matched_required_skills TEXT NOT NULL DEFAULT '[]',missing_required_skills TEXT NOT NULL DEFAULT '[]',application_status TEXT NOT NULL DEFAULT 'new',status_updated_at TEXT,applied_at TEXT,follow_up_days INTEGER NOT NULL DEFAULT 7,follow_up_completed INTEGER NOT NULL DEFAULT 0,is_saved INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '',is_active INTEGER NOT NULL DEFAULT 1,last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,last_notified_at TEXT,last_notified_priority TEXT NOT NULL DEFAULT '',discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""");self._migrate_schema();self.conn.execute("""CREATE TABLE IF NOT EXISTS job_aliases(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER NOT NULL,apply_url TEXT NOT NULL UNIQUE,FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)""");self._backfill_aliases();self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs(application_status)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_saved ON jobs(is_saved)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active)");self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_key ON jobs(job_key)");self.conn.commit()
    def _migrate_schema(self):
        e={r["name"] for r in self.conn.execute("PRAGMA table_info(jobs)").fetchall()};m={"required_skills":"TEXT NOT NULL DEFAULT '[]'","preferred_skills":"TEXT NOT NULL DEFAULT '[]'","general_skills":"TEXT NOT NULL DEFAULT '[]'","matched_required_skills":"TEXT NOT NULL DEFAULT '[]'","missing_required_skills":"TEXT NOT NULL DEFAULT '[]'","application_status":"TEXT NOT NULL DEFAULT 'new'","status_updated_at":"TEXT","applied_at":"TEXT","follow_up_days":"INTEGER NOT NULL DEFAULT 7","follow_up_completed":"INTEGER NOT NULL DEFAULT 0","is_saved":"INTEGER NOT NULL DEFAULT 0","notes":"TEXT NOT NULL DEFAULT ''","is_active":"INTEGER NOT NULL DEFAULT 1","last_seen_at":"TEXT","job_key":"TEXT NOT NULL DEFAULT ''","last_notified_at":"TEXT","last_notified_priority":"TEXT NOT NULL DEFAULT ''"}
        for c,d in m.items():
            if c not in e:self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {c} {d}")
        self.conn.execute("UPDATE jobs SET last_seen_at=COALESCE(last_seen_at,updated_at,discovered_at,CURRENT_TIMESTAMP)")
        for row in self.conn.execute("SELECT id,title,company,location FROM jobs WHERE job_key='' OR job_key IS NULL").fetchall():self.conn.execute("UPDATE jobs SET job_key=? WHERE id=?",(self._job_key(row["title"],row["company"],row["location"]),row["id"]))
    def _backfill_aliases(self):
        for row in self.conn.execute("SELECT id,apply_url FROM jobs").fetchall():self.conn.execute("INSERT OR IGNORE INTO job_aliases(job_id,apply_url) VALUES(?,?)",(row["id"],row["apply_url"]))
    @staticmethod
    def _job_dict(j):
        if isinstance(j,dict):return j
        if hasattr(j,"to_dict"):return j.to_dict()
        return {"title":getattr(j,"title",""),"company":getattr(j,"company",""),"location":getattr(j,"location",""),"apply_url":getattr(j,"apply_url",""),"description":getattr(j,"description",""),"platform":getattr(j,"platform","unknown")}
    @classmethod
    def _row_to_dict(cls,row):
        r=dict(row)
        for c in cls.MATCH_LIST_COLUMNS:r[c]=json.loads(r.get(c) or "[]")
        r["is_saved"]=bool(r.get("is_saved",0));r["is_active"]=bool(r.get("is_active",1));r["follow_up_completed"]=bool(r.get("follow_up_completed",0));r.update(cls._follow_up(r));r["priority_score"]=cls._priority(r);r["priority_label"]=cls._priority_label(r["priority_score"]);return r
