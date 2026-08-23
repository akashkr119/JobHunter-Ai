import pytest

from crawler.source_config import SourceConfig


def test_source_config_normalizes_and_selects_sources():
    config = SourceConfig(enabled=(" Adzuna", "INDEED", "adzuna"), disabled=("LinkedIn",))
    assert config.enabled == ("adzuna", "indeed")
    assert config.selected(("adzuna", "indeed", "linkedin", "naukri")) == ("adzuna", "indeed")


def test_source_config_defaults_to_all_available_except_disabled():
    config = SourceConfig(disabled=("linkedin",))
    assert config.selected(("adzuna", "linkedin", "naukri")) == ("adzuna", "naukri")


def test_source_config_rejects_overlap():
    with pytest.raises(ValueError, match="both enabled and disabled"):
        SourceConfig(enabled=("adzuna",), disabled=("Adzuna",))


def test_source_config_rejects_invalid_retry_count():
    with pytest.raises(ValueError, match="retry_attempts"):
        SourceConfig(retry_attempts=0)
