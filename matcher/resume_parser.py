"""Resume parsing utilities."""
from pathlib import Path
class ResumeParser:
    def extract_text(self,resume_path:str|Path)->str:
        path=Path(resume_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return path.read_text(encoding='utf-8',errors='ignore')
    def parse(self,resume_path:str|Path):
        return self.extract_text(resume_path)
