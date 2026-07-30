"""HTTP client with retries and shared session."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """Reusable HTTP client for web requests."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()

        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({"User-Agent": "JobHunter-AI/1.0"})

    def get(self, url: str, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response
