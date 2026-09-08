import pytest

from matcher.application_package import prepare_application_package


def test_non_string_required_field_is_rejected():
    with pytest.raises(ValueError, match="company"):
        prepare_application_package(
            job_title="QA Engineer",
            company=None,
            apply_url="https://example.com/apply",
            resume_path="resume.pdf",
        )
