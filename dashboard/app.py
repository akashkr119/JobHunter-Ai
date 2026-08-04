"""Dashboard entry point for JobHunter-AI."""

import os

from flask import Flask, jsonify, render_template, request

from database.db import Database

app = Flask(__name__)


def _database_path() -> str:
    return os.getenv("JOBHUNTER_DATABASE_PATH", "jobs.db")


def _list_jobs(min_score: float = 0.0, limit: int = 100, status: str | None = None) -> list[dict]:
    db = Database(_database_path())
    try:
        return db.list_jobs(min_score=min_score, limit=limit, status=status)
    finally:
        db.close()


def _job_summary(job: dict) -> dict:
    return {
        "id": job["id"], "title": job["title"], "company": job["company"],
        "location": job["location"], "platform": job["platform"],
        "match_score": job["match_score"], "matched_skills": job["matched_skills"],
        "missing_skills": job["missing_skills"], "required_skills": job["required_skills"],
        "preferred_skills": job["preferred_skills"],
        "matched_required_skills": job["matched_required_skills"],
        "missing_required_skills": job["missing_required_skills"],
        "application_status": job["application_status"],
        "status_updated_at": job["status_updated_at"],
        "apply_url": job["apply_url"], "discovered_at": job["discovered_at"],
        "updated_at": job["updated_at"],
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


@app.get("/api/jobs")
def jobs():
    try:
        min_score = float(request.args.get("min_score", 0))
        limit = int(request.args.get("limit", 100))
    except ValueError:
        return jsonify({"error": "min_score must be numeric and limit must be an integer"}), 400
    if not 0 <= min_score <= 100:
        return jsonify({"error": "min_score must be between 0 and 100"}), 400
    if not 1 <= limit <= 500:
        return jsonify({"error": "limit must be between 1 and 500"}), 400
    status = request.args.get("status") or None
    try:
        recommendations = [_job_summary(job) for job in _list_jobs(min_score, limit, status)]
    except ValueError as exc:
        return jsonify({"error": str(exc), "allowed_statuses": Database.APPLICATION_STATUSES}), 400
    return jsonify({"count": len(recommendations), "jobs": recommendations})


@app.get("/api/jobs/<int:job_id>")
def job_detail(job_id: int):
    db = Database(_database_path())
    try:
        job = db.get_job(job_id)
    finally:
        db.close()
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.patch("/api/jobs/<int:job_id>/status")
def update_job_status(job_id: int):
    """Update application progress for a saved job."""
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if not status:
        return jsonify({"error": "status is required", "allowed_statuses": Database.APPLICATION_STATUSES}), 400
    db = Database(_database_path())
    try:
        try:
            job = db.update_application_status(job_id, status)
        except ValueError as exc:
            return jsonify({"error": str(exc), "allowed_statuses": Database.APPLICATION_STATUSES}), 400
        except KeyError:
            return jsonify({"error": "Job not found"}), 404
    finally:
        db.close()
    return jsonify(_job_summary(job))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
