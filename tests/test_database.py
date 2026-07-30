"""Unit tests for database layer."""

from database.db import Database


def test_database_instance():
    db = Database()
    assert db is not None


def test_has_connect_method():
    db = Database()
    assert hasattr(db, 'connect')


def test_has_save_job_method():
    db = Database()
    assert hasattr(db, 'save_job')
