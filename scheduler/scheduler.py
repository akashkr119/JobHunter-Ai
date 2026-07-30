"""Scheduling utilities for JobHunter AI."""

from apscheduler.schedulers.blocking import BlockingScheduler


class JobScheduler:
    """Run periodic background jobs."""

    def __init__(self):
        self.scheduler = BlockingScheduler()

    def add_job(self, func, hours: int = 1):
        self.scheduler.add_job(func, trigger="interval", hours=hours)

    def start(self):
        self.scheduler.start()
