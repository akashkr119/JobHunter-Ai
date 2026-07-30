"""Common helper functions used across the application."""

from datetime import datetime
from urllib.parse import urlparse
import re


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def clean_text(text: str) -> str:
    return " ".join(text.split())


def get_domain(url: str) -> str:
    return urlparse(normalize_url(url)).netloc


def current_timestamp() -> str:
    return datetime.utcnow().isoformat()
