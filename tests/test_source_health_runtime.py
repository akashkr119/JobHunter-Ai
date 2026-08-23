import pytest

from crawler.source_health import SourceHealth, SourceStatus
from crawler.source_health_runtime import source_health_provider


class Manager:
    def health(self):
        return (SourceHealth("adzuna", SourceStatus.AVAILABLE),)


def test_provider_reads_live_manager_health():
    provider = source_health_provider(Manager())
    assert provider() == (SourceHealth("adzuna", SourceStatus.AVAILABLE),)


def test_provider_rejects_invalid_manager():
    with pytest.raises(ValueError, match="JobSourceManager"):
        source_health_provider(object())
