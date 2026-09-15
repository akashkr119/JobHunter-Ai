"""Background 24-hour discovery runner for the dashboard instance."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from dashboard.resume_first_discovery import run_discovery
from dashboard.user_config import dashboard_settings, load_config, save_config

INTERVAL_HOURS = 24
_lock = threading.Lock()
_scheduler: BackgroundScheduler | None = None


def _run_if_due() -> None:
    if not _lock.acquire(blocking=False):
        return
    try:
        settings = dashboard_settings()
        state = load_config()
        if not state.get("automatic_search_enabled", True):
            return
        if not settings.target_titles or not settings.preferred_locations:
            return
        try:
            last = datetime.fromisoformat(str(state.get("automatic_search_last_run", "")))
        except ValueError:
            last = None
        now = datetime.now(timezone.utc)
        if last and now - last < timedelta(hours=INTERVAL_HOURS):
            return
        run_discovery(settings)
        state = load_config()
        state["automatic_search_last_run"] = now.isoformat(timespec="seconds")
        save_config(state)
    finally:
        _lock.release()


def start() -> None:
    """Start one in-process scheduler for the single VM dashboard worker."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(_run_if_due, "interval", hours=INTERVAL_HOURS, id="resume-first-discovery", replace_existing=True, max_instances=1, coalesce=True)
    _scheduler.start()
