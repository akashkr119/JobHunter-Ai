"""Resume parsing and skill-extraction utilities."""

import re
from pathlib import Path


class ResumeParser:
    """Extract resume text, skills, and role signals from resumes."""

    DEFAULT_SKILLS = (
        "python", "java", "javascript", "typescript", "c++", "c#", "sql",
        "html", "css", "selenium", "pytest", "playwright", "robot framework",
        "appium", "jira", "git", "github", "jenkins", "docker", "kubernetes",
        "aws", "azure", "gcp", "flask", "django", "fastapi", "pandas", "numpy",
        "rest api", "api testing", "automation testing", "manual testing", "can",
        "canoe", "canalyzer", "capl", "uds", "automotive",
    )

    SUPPORTED_FORMATS = {".txt", ".md", ".pdf", ".docx"}
    ROLE_TOKENS = re.compile(
        r"\b(engineer|developer|tester|testing|sdet|qa|analyst|architect|specialist|"
        r"consultant|manager|lead|administrator|designer|scientist|validation|"
        r"verification|devops|automation)\b",
        re.IGNORECASE,
    )
    ROLE_SENTENCE_STARTS = re.compile(
        r"^(experienced|responsible|worked|working|developed|created|managed|led|"
        r"handled|designed|performed|proficient|skilled|currently|having|with|seeking)\b",
        re.IGNORECASE,
    )

    def extract_text(self, resume_path: str | Path) -> str:
        """Extract text from TXT, Markdown, PDF or DOCX resumes."""
        path = Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Resume path is not a file: {path}")

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            supported = ", ".join(sorted(self.SUPPORTED_FORMATS))
            raise ValueError(
                f"Unsupported resume format: {suffix or 'unknown'}. "
                f"Currently supported: {supported}"
            )

        if suffix in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
        elif suffix == ".pdf":
            text = self._extract_pdf(path)
        else:
            text = self._extract_docx(path)

        return self._clean_text(text)

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        """Extract text from a text-based PDF resume."""
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF parsing requires the pypdf package") from exc

        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages)

    @staticmethod
    def _extract_docx(path: Path) -> str:
        """Extract paragraphs and table text from a DOCX resume."""
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX parsing requires the python-docx package") from exc

        document = Document(str(path))
        parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        parts.append(cell.text)
        return "\n".join(parts)

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

    def extract_roles(self, text: str) -> list[str]:
        """Extract concise role/title lines that actually appear in the resume."""
        found: list[str] = []
        seen: set[str] = set()
        for raw_line in str(text or "").splitlines():
            line = re.sub(r"^[\s•\-*|]+", "", raw_line).strip()
            line = re.sub(r"\s+", " ", line)
            if not line or len(line) > 90 or len(line.split()) > 8:
                continue
            if self.ROLE_SENTENCE_STARTS.search(line) or not self.ROLE_TOKENS.search(line):
                continue
            if sum(char in line for char in ".;:") > 1:
                continue
            key = line.casefold()
            if key not in seen:
                seen.add(key)
                found.append(line)
        return found[:12]

    def parse(self, resume_path: str | Path) -> dict:
        """Parse a resume into normalized text, detected skills, and role signals."""
        path = Path(resume_path)
        text = self.extract_text(path)
        return {
            "path": str(path),
            "format": path.suffix.lower().lstrip("."),
            "text": text,
            "skills": self.extract_skills(text),
            "roles": self.extract_roles(text),
        }

    @staticmethod
    def _clean_text(value: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in str(value or "").splitlines()]
        return "\n".join(line for line in lines if line).strip()

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize text for deterministic skill matching."""
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()
