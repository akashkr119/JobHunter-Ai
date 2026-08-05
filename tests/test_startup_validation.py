from pathlib import Path
import pytest
from config.settings import Settings
from main import validate_startup

def settings(tmp_path,**kwargs):
    resume=tmp_path/"resume.txt";resume.write_text("Python Selenium",encoding="utf-8");values={"database_path":str(tmp_path/"state"/"jobs.db"),"resume_path":str(resume),"run_history_path":str(tmp_path/"history"/"runs.jsonl"),"run_lock_path":str(tmp_path/"locks"/"runner.lock")};values.update(kwargs);return Settings(**values)

def test_valid_startup_creates_runtime_directories(tmp_path):
    s=settings(tmp_path);validate_startup(["https://boards.greenhouse.io/example"],s);assert Path(s.database_path).parent.is_dir();assert Path(s.run_history_path).parent.is_dir();assert Path(s.run_lock_path).parent.is_dir()
def test_missing_resume_fails_before_runtime(tmp_path):
    s=settings(tmp_path,resume_path=str(tmp_path/"missing.pdf"))
    with pytest.raises(ValueError,match="Resume file not found"):validate_startup(["https://example.com/jobs"],s)
def test_empty_sources_are_rejected(tmp_path):
    with pytest.raises(ValueError,match="at least one career URL"):validate_startup([],settings(tmp_path))
@pytest.mark.parametrize("url",["example.com/jobs","ftp://example.com/jobs","not a url","",None])
def test_invalid_career_urls_are_rejected(tmp_path,url):
    with pytest.raises(ValueError,match="Invalid career URL"):validate_startup([url],settings(tmp_path))
def test_http_and_https_sources_are_allowed(tmp_path):
    validate_startup(["http://example.com/jobs","https://jobs.example.com"],settings(tmp_path))
def test_invalid_notification_credentials_fail_at_startup(tmp_path):
    s=settings(tmp_path,notification_channel="telegram",telegram_bot_token=None,telegram_chat_id=None)
    with pytest.raises(ValueError,match="Telegram notification"):validate_startup(["https://example.com/jobs"],s)
