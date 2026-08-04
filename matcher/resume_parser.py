"""Resume parsing and skill-extraction utilities."""

import re
from pathlib import Path


class ResumeParser:
    """Extract resume text and identify common technical skills."""

    DEFAULT_SKILLS = (
        "python",
        "java",
        "javascript",
        "typescript",
        "c++",
        "c#",
        "sql",
        "html",
        "css",
        "selenium",
        "pytest",
        "playwright",
        "robot framework",
        "appium",
        "jira",
        "git",
        "github",
        "jenkins",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "flask",
        "django",
        "fastapi",
        "pandas",
        "numpy",
        "rest api",
        "api testing",
        "automation testing",
        "manual testing",
        "can",
        "canoe",
        "canalyzer",
        "capl",
        "uds",
        "automotive",
    )

    def extract_text(self, resume_path: str | Path) -> str:
        """Read a plain-text resume from disk.

        PDF and DOCX extraction will be added through dedicated parsers; this
        method intentionally rejects binary formats instead of returning
        corrupted text.
        """
        path = Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Resume path is not a file: {path}")

        suffix = path.suffix.lower()
        if suffix not in {".txt", ".md"}:
            raise ValueError(
                f"Unsupported resume format: {suffix or 'unknown'}. "
                "Currently supported: .txt, .md"
            )

        return path.read_text(encoding="utf-8", errors="ignore").strip()

    def extract_skills(
        self,
        text: str,
        skills: list[str] | tuple[str, ...] | None = None,
    ) -> list[str]:
        """Return known skills found in resume text, preserving skill order."""
        normalized_text = self._normalize(text)
        candidates = skills or self.DEFAULT_SKILLS
        found: list[str] = []

        for skill in candidates:
            normalized_skill = self._normalize(str(skill))
            if not normalized_skill:
                continue

            pattern = rf"(?<![a-z0-9]){re.escape(normalized_skill)}(?![a-z0-9])"
            if re.search(pattern, normalized_text) and normalized_skill not in found:
                found.append(normalized_skill)

        return found

    def parse(self, resume_path: str | Path) -> dict:
        """Parse a resume into normalized text and detected skills."""
        text = self.extract_text(resume_path)
        return {
            "path": str(Path(resume_path)),
            "text": text,
            "skills": self.extract_skills(text),
        }

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize text for deterministic skill matching."""
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()
