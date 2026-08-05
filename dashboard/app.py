"""Dashboard entry point for JobHunter-AI."""
import os
from flask import Flask,jsonify,render_template,request
from database.db import Database
app=Flask(__name__)
def _database_path():return os.getenv("JOBHUNTER_DATABASE_PATH","jobs.db")
def _list_jobs(min_score=0.0,limit=100,status=None,saved=None):
    db=Database(_database_path())
    try:return db.list_jobs(min_score=min_score,limit=limit,status=status,saved=saved)
    finally:db.close()
def _job_summary(job):
    keys=("id","title","company","location","platform","match_score","matched_skills","missing_skills","required_skills","preferred_skills","matched_required_skills","missing_required_skills","application_status","status_updated_at","is_saved","notes","apply_url","discovered_at","updated_at")
    return {k:job[k] for k in keys}
@app.get("/")
def home():return render_template("index.html")
@app.get("/health")
def health():return jsonify({"status":"healthy"})
@app.get("/api/analytics")
def analytics():
    db=Database(_database_path())
    try:return jsonify(db.get_analytics())
    finally:db.close()
@app.get("/api/jobs")
def jobs():
    try:min_score=float(request.args.get("min_score",0));limit=int(request.args.get("limit",100))
    except ValueError:return jsonify({"error":"min_score must be numeric and limit must be an integer"}),400
    if not 0<=min_score<=100:return jsonify({"error":"min_score must be between 0 and 100"}),400
    if not 1<=limit<=500:return jsonify({"error":"limit must be between 1 and 500"}),400
    status=request.args.get("status") or None;saved_arg=request.args.get("saved");saved=None
    if saved_arg is not None:
        if saved_arg.lower() not in ("true","false","1","0"):return jsonify({"error":"saved must be true or false"}),400
        saved=saved_arg.lower() in ("true","1")
    try:recommendations=[_job_summary(j) for j in _list_jobs(min_score,limit,status,saved)]
    except ValueError as exc:return jsonify({"error":str(exc),"allowed_statuses":Database.APPLICATION_STATUSES}),400
    return jsonify({"count":len(recommendations),"jobs":recommendations})
@app.get("/api/jobs/<int:job_id>")
def job_detail(job_id):
    db=Database(_database_path())
    try:job=db.get_job(job_id)
    finally:db.close()
    if job is None:return jsonify({"error":"Job not found"}),404
    return jsonify(job)
@app.patch("/api/jobs/<int:job_id>/status")
def update_job_status(job_id):
    payload=request.get_json(silent=True) or {};status=payload.get("status")
    if not status:return jsonify({"error":"status is required","allowed_statuses":Database.APPLICATION_STATUSES}),400
    db=Database(_database_path())
    try:
        try:job=db.update_application_status(job_id,status)
        except ValueError as exc:return jsonify({"error":str(exc),"allowed_statuses":Database.APPLICATION_STATUSES}),400
        except KeyError:return jsonify({"error":"Job not found"}),404
    finally:db.close()
    return jsonify(_job_summary(job))
@app.patch("/api/jobs/<int:job_id>/tracking")
def update_job_tracking(job_id):
    payload=request.get_json(silent=True) or {}
    if "saved" not in payload and "notes" not in payload:return jsonify({"error":"saved or notes is required"}),400
    if "saved" in payload and not isinstance(payload["saved"],bool):return jsonify({"error":"saved must be a boolean"}),400
    db=Database(_database_path())
    try:
        try:job=db.update_job_tracking(job_id,saved=payload.get("saved") if "saved" in payload else None,notes=payload.get("notes") if "notes" in payload else None)
        except ValueError as exc:return jsonify({"error":str(exc)}),400
        except KeyError:return jsonify({"error":"Job not found"}),404
    finally:db.close()
    return jsonify(_job_summary(job))
if __name__=="__main__":app.run(host="0.0.0.0",port=5000,debug=True)
