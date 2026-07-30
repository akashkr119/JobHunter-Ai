"""Unit tests for scheduler."""

from scheduler.scheduler import Scheduler


def test_scheduler_instance():
    scheduler = Scheduler()
    assert scheduler is not None


def test_has_start_method():
    scheduler = Scheduler()
    assert hasattr(scheduler, 'start')


def test_start_method_is_callable():
    scheduler = Scheduler()
    assert callable(scheduler.start)
