"""Unit tests for notifier."""

from notifier.notifier import Notifier


def test_notifier_instance():
    notifier = Notifier()
    assert notifier is not None


def test_has_send_method():
    notifier = Notifier()
    assert hasattr(notifier, 'send')


def test_send_method_is_callable():
    notifier = Notifier()
    assert callable(notifier.send)
