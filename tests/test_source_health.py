from crawler.source_health import SourceStatus, evaluate_source_health


def test_health_marks_success_and_failure():
    health = evaluate_source_health(
        ["Adzuna", "LinkedIn", "Naukri"],
        [("adzuna", True, None), ("linkedin", False, "unauthorized")],
    )

    assert health[0].status is SourceStatus.AVAILABLE
    assert health[1].status is SourceStatus.FAILED
    assert health[1].message == "unauthorized"
    assert health[2].status is SourceStatus.CONFIGURED


def test_health_marks_disabled_source():
    health = evaluate_source_health(
        ["indeed", "naukri"],
        [],
        disabled_sources=["Indeed"],
    )

    assert health[0].status is SourceStatus.DISABLED
    assert health[1].status is SourceStatus.CONFIGURED


def test_health_normalizes_source_names_and_skips_empty_names():
    health = evaluate_source_health(
        [" LinkedIn ", ""],
        [("LINKEDIN", True, None)],
    )

    assert health == (
        health[0],
    )
    assert health[0].source == "linkedin"
    assert health[0].status is SourceStatus.AVAILABLE
