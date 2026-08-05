"""Regression checks for the V1 release contract."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def env_keys(path):
    keys=set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if line and not line.startswith("#") and "=" in line:keys.add(line.split("=",1)[0].strip())
    return keys

def test_release_files_exist():
    for relative in ("README.md","CHANGELOG.md","docs/PRODUCTION.md",".env.example","requirements.txt","pytest.ini","main.py","app.py"):
        assert (ROOT/relative).is_file(),f"Missing V1 release file: {relative}"

def test_env_example_covers_production_settings():
    required={"JOBHUNTER_DATABASE_PATH","JOBHUNTER_RESUME_PATH","JOBHUNTER_MIN_MATCH_SCORE","JOBHUNTER_SCHEDULER_HOURS","JOBHUNTER_TARGET_TITLES","JOBHUNTER_PREFERRED_LOCATIONS","JOBHUNTER_WORK_MODES","JOBHUNTER_DESIRED_KEYWORDS","JOBHUNTER_EXCLUDED_KEYWORDS","JOBHUNTER_LOG_LEVEL","JOBHUNTER_RUN_HISTORY_PATH","JOBHUNTER_RUN_LOCK_PATH","JOBHUNTER_NOTIFICATION_CHANNEL","JOBHUNTER_NOTIFICATION_MIN_PRIORITY","JOBHUNTER_NOTIFICATION_MIN_RECOMMENDATION_SCORE","JOBHUNTER_TELEGRAM_BOT_TOKEN","JOBHUNTER_TELEGRAM_CHAT_ID","JOBHUNTER_SMTP_HOST","JOBHUNTER_SMTP_PORT","JOBHUNTER_SMTP_USERNAME","JOBHUNTER_SMTP_PASSWORD","JOBHUNTER_SMTP_SENDER","JOBHUNTER_EMAIL_RECIPIENT"}
    assert required<=env_keys(ROOT/".env.example")

def test_env_example_contains_no_real_secrets():
    text=(ROOT/".env.example").read_text(encoding="utf-8")
    values={line.split("=",1)[0]:line.split("=",1)[1].strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#") and "=" in line}
    for key in ("JOBHUNTER_TELEGRAM_BOT_TOKEN","JOBHUNTER_TELEGRAM_CHAT_ID","JOBHUNTER_SMTP_USERNAME","JOBHUNTER_SMTP_PASSWORD","JOBHUNTER_SMTP_SENDER","JOBHUNTER_EMAIL_RECIPIENT"):
        assert values.get(key,"")=="",f"{key} must remain blank in .env.example"

def test_gitignore_protects_runtime_secrets_and_state():
    text=(ROOT/".gitignore").read_text(encoding="utf-8").splitlines();rules={line.strip() for line in text if line.strip() and not line.lstrip().startswith("#")};assert ".env" in rules;assert "*.db" in rules;assert "logs/" in rules

def test_readme_marks_final_v1_milestone_in_release_validation():
    text=(ROOT/"README.md").read_text(encoding="utf-8");assert "| 5 | Automated Production Runner | ✅ Complete |" in text;assert "| 6 | V1 Hardening & Release | 🧪 Release validation |" in text;assert "After both pass, the repository can be tagged `v1.0.0`." in text

def test_changelog_has_v1_release_gate():
    text=(ROOT/"CHANGELOG.md").read_text(encoding="utf-8");assert "## [1.0.0] - Unreleased" in text;assert "Tag `v1.0.0` only after the full CI suite passes" in text

def test_production_docs_cover_safety_and_operations():
    text=(ROOT/"docs/PRODUCTION.md").read_text(encoding="utf-8").lower()
    for phrase in ("never commit real notification credentials","single-instance lock","sigint/sigterm","run history","pytest suite is green"):
        assert phrase in text
