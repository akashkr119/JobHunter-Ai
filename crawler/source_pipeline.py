"""Run normalized multi-source jobs through the existing JobHunter pipeline."""

from crawler.job_source import JobSearchRequest
from matcher.job_preferences import JobPreferences


def process_source_jobs(
    scheduler,
    request: JobSearchRequest,
    resume_skills,
    *,
    sources=None,
    min_score: float = 0.0,
    notification: dict | None = None,
    preferences: JobPreferences | dict | None = None,
) -> dict:
    """Search sources and apply the same match/preference/persistence rules as ATS jobs."""
    if not 0 <= float(min_score) <= 100:
        raise ValueError("min_score must be between 0 and 100")

    prefs = preferences if isinstance(preferences, JobPreferences) else JobPreferences.from_dict(preferences)
    summary = {
        "sources": 0,
        "jobs_found": 0,
        "jobs_saved": 0,
        "jobs_skipped": 0,
        "jobs_preference_excluded": 0,
        "notifications_sent": 0,
        "notifications_suppressed": 0,
        "errors": [],
    }
    selected = tuple(sources) if sources is not None else scheduler.source_manager.names()
    summary["sources"] = len(selected)

    jobs = scheduler.search_sources(request, sources=selected)
    summary["jobs_found"] = len(jobs)
    skills = tuple(resume_skills)

    for job in jobs:
        apply_url = str(getattr(job, "apply_url", "") or "").strip()
        try:
            preference = prefs.evaluate(job)
            if preference["excluded_keywords"]:
                summary["jobs_preference_excluded"] += 1
                summary["jobs_skipped"] += 1
                scheduler._diagnose_skip(job, "preference", preference.get("excluded_keywords"), None, min_score)
                continue

            match = scheduler.matcher.match_job(skills, job)
            match["preference_score"] = preference["preference_score"]
            match["preference_match"] = preference["preference_match"]
            match["preference_details"] = preference
            if match["score"] < float(min_score):
                summary["jobs_skipped"] += 1
                scheduler._diagnose_skip(job, "score", None, match, min_score)
                continue

            existing = scheduler._existing_job(job)
            job_id = scheduler.database.save_job(job, match=match)
            summary["jobs_saved"] += 1
            stored = scheduler.database.get_job(job_id)

            if notification and scheduler.notifier:
                should_notify = scheduler._should_notify(stored, existing, notification)
                if should_notify:
                    scheduler._notify(job, match, notification, stored)
                    scheduler.database.mark_job_notified(job_id, stored["priority_label"])
                    summary["notifications_sent"] += 1
                else:
                    summary["notifications_suppressed"] += 1
        except Exception as exc:
            summary["errors"].append({
                "source": str(getattr(job, "platform", "unknown") or "unknown"),
                "apply_url": apply_url,
                "stage": "source_pipeline",
                "error": str(exc),
            })

    return summary
