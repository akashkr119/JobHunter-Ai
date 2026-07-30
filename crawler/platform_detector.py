"""Detect applicant tracking systems (ATS) from career page URLs."""


class PlatformDetector:
    """Identify common ATS providers using URL patterns."""

    ATS_PATTERNS = {
        "workday": "workday",
        "greenhouse": "greenhouse.io",
        "lever": "lever.co",
        "smartrecruiters": "smartrecruiters.com",
        "oracle": "oraclecloud.com",
        "successfactors": "successfactors",
        "icims": "icims.com",
        "ashby": "ashbyhq.com",
        "bamboohr": "bamboohr.com",
    }

    def detect(self, url: str) -> str:
        target = url.lower()
        for platform, pattern in self.ATS_PATTERNS.items():
            if pattern in target:
                return platform
        return "unknown"
