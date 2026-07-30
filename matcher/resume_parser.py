"""Resume parsing utilities."""

from pathlib import Path


class ResumeParser:
    """Basic resume parser placeholder."""

    def extract_text(self, resume_path: str | Path) -> str:
        """Extract text from a resume file.

        PDF and DOCX support will be added in future revisions.
        """
        path = Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(path)

        return path.read_text(encoding="utf-8", errors="ignore")
