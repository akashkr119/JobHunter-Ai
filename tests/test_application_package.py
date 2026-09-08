import pytest

from matcher.application_package import prepare_application_package


def test_prepare_application_package_normalizes_review_data():
    package = prepare_application_package(
        job_title=" QA Engineer ",
        company=" Example Corp ",
        apply_url=" https://example.com/apply ",
        resume_path=" resume.pdf ",
        cover_letter=" Hello ",
        answers={" Notice period ": " 30 days ", "": "ignored"},
    )

    assert package.job_title == "QA Engineer"
    assert package.company == "Example Corp"
    assert package.apply_url == "https://example.com/apply"
    assert package.resume_path == "resume.pdf"
    assert package.cover_letter == "Hello"
    assert package.answers == (("Notice period", "30 days"),)
    assert package.ready_for_review is True


def test_required_application_fields_are_validated():
    with pytest.raises(ValueError, match="job_title"):
        prepare_application_package(
            job_title="",
            company="Example",
            apply_url="https://example.com",
            resume_path="resume.pdf",
        )


def test_package_does_not_submit_application():
    package = prepare_application_package(
        job_title="QA Engineer",
        company="Example",
        apply_url="https://example.com/apply",
        resume_path="resume.pdf",
    )

    assert package.ready_for_review is True
    assert not hasattr(package, "submit")
