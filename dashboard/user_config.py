"""Persistent single-user dashboard configuration and resume storage helpers."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from config.settings import Settings

MAX_RESUME_BYTES = 10 * 1024 * 1024
SUPPORTED_RESUME_FORMATS = {".pdf", ".docx", ".txt", ".md"}
CONFIG_ENV = "JOBHUNTER_DASHBOARD_CONFIG_PATH"
DEFAULT_CONFIG_PATH = Path("data/dashboard_settings.json")


def config_path() -> Path:
    path = Path(os.getenv(CONFIG_ENV, str(DEFAULT_CONFIG_PATH))).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_config() -> dict:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict) -> None:
    path = config_path()
    payload = json.dumps(data, indent=2, sort_keys=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _csv_values(value) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def dashboard_settings() -> Settings:
    """Build Settings from environment defaults plus persisted browser configuration."""
    base = Settings.from_env()
    saved = load_config()
    values = {
        "resume_path": str(saved.get("resume_path") or base.resume_path),
        "min_match_score": float(saved.get("min_match_score", base.min_match_score)),
        "target_titles": _csv_values(saved.get("target_titles", base.target_titles)),
        "preferred_locations": _csv_values(saved.get("preferred_locations", base.preferred_locations)),
        "work_modes": _csv_values(saved.get("work_modes", base.work_modes)),
        "desired_keywords": _csv_values(saved.get("desired_keywords", base.desired_keywords)),
        "excluded_keywords": _csv_values(saved.get("excluded_keywords", base.excluded_keywords)),
    }
    from dataclasses import replace

    return replace(base, **values)


def dashboard_state() -> dict:
    settings = dashboard_settings()
    saved = load_config()
    resume = Path(settings.resume_path).expanduser()
    return {
        "resume": {
            "configured": resume.is_file(),
            "filename": resume.name if resume.is_file() else None,
            "format": resume.suffix.lower().lstrip(".") if resume.is_file() else None,
            "path_configured": str(resume),
        },
        "preferences": {
            "min_match_score": settings.min_match_score,
            "target_titles": list(settings.target_titles),
            "preferred_locations": list(settings.preferred_locations),
            "work_modes": list(settings.work_modes),
            "desired_keywords": list(settings.desired_keywords),
            "excluded_keywords": list(settings.excluded_keywords),
        },
        "career_urls": list(saved.get("career_urls") or []),
    }


def update_preferences(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("JSON object is required")
    current = load_config()
    fields = (
        "target_titles",
        "preferred_locations",
        "work_modes",
        "desired_keywords",
        "excluded_keywords",
    )
    for field in fields:
        if field in payload:
            values = _csv_values(payload[field])
            if len(values) > 30:
                raise ValueError(f"{field} may contain at most 30 values")
            current[field] = list(values)
    if "min_match_score" in payload:
        try:
            score = float(payload["min_match_score"])
        except (TypeError, ValueError) as exc:
            raise ValueError("min_match_score must be numeric") from exc
        if not 0 <= score <= 100:
            raise ValueError("min_match_score must be between 0 and 100")
        current["min_match_score"] = score
    if "career_urls" in payload:
        urls = _csv_values(payload["career_urls"])
        if not 1 <= len(urls) <= 20:
            raise ValueError("career_urls must contain between 1 and 20 URLs")
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid career URL: {url}")
            if parsed.username or parsed.password:
                raise ValueError("Career URLs must not contain credentials")
        current["career_urls"] = list(urls)
    save_config(current)
    return dashboard_state()


def _resume_suffix(file_storage, original_name: str, initial_bytes: bytes) -> str:
    """Resolve a resume format when mobile browsers omit the filename extension."""
    suffix = Path(original_name).suffix.lower()
    if suffix in SUPPORTED_RESUME_FORMATS:
        return suffix
    if suffix:
        raise ValueError("Unsupported resume format. Use PDF, DOCX, TXT or MD")

    mimetype = str(getattr(file_storage, "mimetype", "") or "").lower().split(";", 1)[0].strip()
    mime_formats = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
        "text/markdown": ".md",
    }
    if mimetype in mime_formats:
        return mime_formats[mimetype]
    if initial_bytes.startswith(b"%PDF-"):
        return ".pdf"
    if initial_bytes.startswith(b"PK\x03\x04") and b"[Content_Types].xml" in initial_bytes:
        return ".docx"
    raise ValueError("Unsupported resume format. Use PDF, DOCX, TXT or MD")


def store_resume(file_storage) -> dict:
    """Validate, parse, and atomically activate a browser-uploaded resume."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise ValueError("A resume file is required")
    original_name = Path(str(file_storage.filename)).name
    stream = getattr(file_storage, "stream", file_storage)
    initial_bytes = stream.read(4096)
    if hasattr(stream, "seek"):
        stream.seek(0)
    suffix = _resume_suffix(file_storage, original_name, initial_bytes)

    from matcher.resume_parser import ResumeParser

    resume_dir = config_path().parent / "resumes"
    resume_dir.mkdir(parents=True, exist_ok=True)
    target = resume_dir / f"active{suffix}"
    fd, temporary = tempfile.mkstemp(prefix=".resume-", suffix=suffix, dir=resume_dir)
    try:
        total = 0
        with os.fdopen(fd, "wb") as handle:
            if initial_bytes:
                handle.write(initial_bytes)
                total = len(initial_bytes)
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESUME_BYTES:
                    raise ValueError("Resume must be 10 MB or smaller")
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        parsed = ResumeParser().parse(temporary)
        if not parsed["text"]:
            raise ValueError("Resume contains no extractable text")
        os.replace(temporary, target)
        current = load_config()
        current["resume_path"] = str(target)
        current["resume_filename"] = original_name
        save_config(current)
        return {"filename": original_name, "format": suffix.lstrip("."), "skills": parsed["skills"], "path": str(target)}
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
