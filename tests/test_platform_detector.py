"""Unit tests for platform detector."""

from crawler.platform_detector import PlatformDetector


def test_platform_detector_instance():
    detector = PlatformDetector()
    assert detector is not None


def test_has_detect_method():
    detector = PlatformDetector()
    assert hasattr(detector, 'detect')


def test_detect_method_is_callable():
    detector = PlatformDetector()
    assert callable(detector.detect)
