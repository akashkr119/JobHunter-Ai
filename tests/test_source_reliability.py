import pytest

from crawler.source_reliability import SourceReliabilityTracker, retry_call


def test_tracker_records_success_failure_and_history():
    tracker = SourceReliabilityTracker()
    tracker.start("Adzuna")
    tracker.success("adzuna", jobs_returned=4)
    tracker.start("ADZUNA")
    tracker.failure("adzuna", "timeout")

    metric = tracker.snapshot()[0]
    assert metric.source == "adzuna"
    assert metric.runs == 2
    assert metric.successes == 1
    assert metric.failures == 1
    assert metric.jobs_returned == 4
    assert metric.success_rate == 50.0
    assert metric.last_error == "timeout"


def test_retry_call_retries_then_succeeds():
    calls = []

    def operation():
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("temporary")
        return "ok"

    assert retry_call(operation, attempts=2) == "ok"
    assert len(calls) == 2


def test_retry_call_rejects_invalid_attempts():
    with pytest.raises(ValueError, match="at least 1"):
        retry_call(lambda: None, attempts=0)
