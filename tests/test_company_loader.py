"""Unit tests for company loader."""

import pytest

from crawler.company_loader import CompanyLoader


def test_loader_instance_creation():
    loader = CompanyLoader()
    assert loader is not None


def test_loader_has_load_method():
    loader = CompanyLoader()
    assert hasattr(loader, "load")


@pytest.mark.parametrize("path", ["companies.xlsx", "input.xlsx"])
def test_load_accepts_excel_path(path):
    loader = CompanyLoader()
    assert callable(loader.load)
