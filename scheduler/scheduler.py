"""Scheduling utilities for JobHunter AI."""

from apscheduler.schedulers.blocking import BlockingScheduler

class Scheduler:
    """Simple scheduler wrapper expected by tests."""

    def __init__(self):
        self._scheduler = BlockingScheduler()

    def add_job(self, func, hours: int = 1):
        self._scheduler.add_job(func, trigger="interval", hours=hours)

    def start(self):
        self._scheduler.start()

class JobScheduler(Scheduler):
    """Backward-compatible alias."""
    pass
