"""Resume parsing and skill-extraction utilities."""

import re
from pathlib import Path


class ResumeParser:
    """Extract resume text and identify technical skills conservatively."""

    DEFAULT_SKILLS = (
        "python", "java", "javascript", "typescript", "c++", "c#", "sql",
        "html", "css", "selenium", "pytest", "playwright", "robot framework",
        "appium", "postman", "jira", "git", "github", "gitlab", "jenkins",
        "docker", "kubernetes", "aws", "azure", "gcp", "flask", "django",
        "fastapi", "pandas", "numpy", "rest api", "api testing",
        "automation testing", "manual testing", "integration testing",
        "system testing", "regression testing", "software testing", "wireshark",
        "ethernet", "tcp/ip", "udp", "linux", "bash", "powershell", "agile",
        "scrum", "ci/cd", "can bus", "canoe", "canalyzer", "capl", "uds",
        "autosar", "dlt", "automotive", "embedded systems", "embedded testing",
        "vehicle testing", "system validation", "system verification",
        "requirements testing", "v-model", "soap api", "graphql", "microservices",
        "oracle", "mysql", "postgresql", "mongodb", "redis", "terraform",
    )

    SKILL_ALIASES = {
        "selenium webdriver": "selenium",
        "selenium web driver": "selenium",
        "restful api": "rest api",
        "rest apis": "rest api",
        "restful apis": "rest api",
        "rest api testing": "api testing",
        "api automation": "api testing",
        "web api testing": "api testing",
        "test automation": "automation testing",
        "automated testing": "automation testing",
        "automation test": "automation testing",
        "continuous integration": "ci/cd",
        "continuous delivery": "ci/cd",
        "ci cd": "ci/cd",
        "controller area network": "can bus",
        "can network": "can bus",
        "can protocol": "can bus",
        "can communication": "can bus",
        "embedded system": "embedded systems",
        "vehicle validation": "vehicle testing",
    }

    SUPPORTED_FORMATS = {".txt", ".md", ".pdf", ".docx"}

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
            raise ValueError(f"Unsupported resume format: {suffix or 'unknown'}. Currently supported: {supported}")
        if suffix in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
        elif suffix == ".pdf":
            text = self._extract_pdf(path)
        else:
            text = self._extract_docx(path)
        return self._clean_text(text)

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF parsing requires the pypdf package") from exc
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _extract_docx(path: Path) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX parsing requires the python-docx package") from exc
        document = Document(str(path))
        parts = [p.text for p in document.paragraphs if p.text]
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        parts.append(cell.text)
        return "\n".join(parts)

    def extract_skills(self, text: str, skills: list[str] | tuple[str, ...] | None = None) -> list[str]:
        """Return known skills found in text, normalized to canonical names."""
        original = str(text or "")
        normalized_text = self._normalize(original)
        candidates = skills or self.DEFAULT_SKILLS
        found: list[str] = []
        for skill in candidates:
            normalized_skill = self._normalize(str(skill))
            if not normalized_skill:
                continue
            aliases = {normalized_skill}
            aliases.update(alias for alias, canonical in self.SKILL_ALIASES.items() if canonical == normalized_skill)
            if any(self._contains_skill(normalized_text, alias) for alias in aliases):
                canonical = self.SKILL_ALIASES.get(normalized_skill, normalized_skill)
                if canonical not in found:
                    found.append(canonical)

        # A bare lowercase "can" is ordinary English. Only recognize CAN as a
        # technology when the resume explicitly uses it with a CAN-bus context.
        if re.search(r"(?<![A-Za-z])CAN(?![A-Za-z])", original) and re.search(
            r"(?i)\bCAN\s+(?:bus|protocol|communication|network|messages?|signals?)\b", original,
        ) and "can bus" not in found:
            found.append("can bus")
        return found

    @staticmethod
    def _contains_skill(text: str, skill: str) -> bool:
        normalized = re.sub(r"\s+", " ", str(skill or "").lower()).strip()
        if not normalized:
            return False
        pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
        return bool(re.search(pattern, text))

    def parse(self, resume_path: str | Path) -> dict:
        path = Path(resume_path)
        text = self.extract_text(path)
        return {"path": str(path), "format": path.suffix.lower().lstrip("."), "text": text, "skills": self.extract_skills(text)}

    @staticmethod
    def _clean_text(value: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in str(value or "").splitlines()]
        return "\n".join(line for line in lines if line).strip()

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()
