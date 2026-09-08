from matcher.resume_gap import analyze_resume_gap


def test_gap_analysis_reports_matched_and_missing_skills():
    result = analyze_resume_gap(
        "Python, SQL and Selenium testing experience",
        "Looking for Python, SQL, Selenium and Docker experience",
    )

    assert result.resume_skills == ("python", "sql", "selenium")
    assert result.job_skills == ("python", "sql", "selenium", "docker")
    assert result.matched_skills == ("python", "sql", "selenium")
    assert result.missing_skills == ("docker",)
    assert result.match_ratio == 0.75


def test_gap_analysis_accepts_parsed_resume_data():
    result = analyze_resume_gap(
        {"skills": ["Python", "SQL"]},
        "Python and Docker required",
    )

    assert result.resume_skills == ("python", "sql")
    assert result.missing_skills == ("docker",)


def test_gap_analysis_does_not_invent_missing_skills():
    result = analyze_resume_gap(
        ["python"],
        "Communication and leadership experience required",
    )

    assert result.job_skills == ()
    assert result.missing_skills == ()
    assert result.match_ratio == 1.0
