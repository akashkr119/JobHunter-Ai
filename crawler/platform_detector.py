"""Detect applicant tracking systems (ATS) from career page data."""

from urllib.parse import urlparse


class PlatformDetector:
    """Identify common ATS providers using URL and page-content patterns."""

    ATS_PATTERNS = {
        "workday": (
            "workday.com",
            "myworkdayjobs.com",
            "myworkdaysite.com",
            "/wday/cxs/",
        ),
        "greenhouse": ("greenhouse.io", "boards-api.greenhouse.io"),
        "lever": ("lever.co", "api.lever.co"),
        "smartrecruiters": ("smartrecruiters.com", "api.smartrecruiters.com"),
        "oracle": ("oraclecloud.com", "oracle.com/hcm"),
        "successfactors": ("successfactors", "successfactors.com"),
        "icims": ("icims.com",),
        "ashby": ("ashbyhq.com",),
        "bamboohr": ("bamboohr.com",),
        "jobvite": ("jobvite.com",),
        "taleo": ("taleo.net",),
        "recruitee": ("recruitee.com",),
        "personio": ("personio.de", "personio.com"),
        "teamtailor": ("teamtailor.com",),
    }

    def detect(self, url: str, page_content: str | None = None) -> str:
        """Return the detected ATS name or ``unknown`` when no match exists."""
        if url is None:
            raise ValueError("Career page URL cannot be empty")

        target = str(url).strip().lower()
        if not target:
            raise ValueError("Career page URL cannot be empty")

        searchable = target
        if page_content:
            searchable = f"{searchable}\n{str(page_content).lower()}"

        for platform, patterns in self.ATS_PATTERNS.items():
            if any(pattern in searchable for pattern in patterns):
                return platform

        return "unknown"

    def is_supported(self, platform: str) -> bool:
        """Return whether the detector knows the supplied ATS platform."""
        if not platform:
            return False
        return str(platform).strip().lower() in self.ATS_PATTERNS

    @staticmethod
    def hostname(url: str) -> str:
        """Return a normalized hostname from a URL."""
        if not url:
            return ""
        candidate = str(url).strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        return (urlparse(candidate).hostname or "").lower()
