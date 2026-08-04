"""Load company targets from Excel files."""

from pathlib import Path

import pandas as pd


class CompanyLoader:
    """Load company names or structured company targets from Excel."""

    COMPANY_COLUMN_NAMES = (
        "company", "company name", "company_name", "organization", "organisation",
    )
    WEBSITE_COLUMN_NAMES = (
        "website", "website url", "website_url", "company website", "company_website",
    )
    CAREER_COLUMN_NAMES = (
        "career", "careers", "career url", "career_url", "careers url", "careers_url",
        "jobs url", "jobs_url",
    )

    def load(self, excel_path: str | Path, company_column: str | None = None) -> list[str]:
        """Return unique company names, preserving the original public API."""
        df = self._read(excel_path)
        if df.empty or len(df.columns) == 0:
            return []
        column = self._resolve_column(df, company_column, self.COMPANY_COLUMN_NAMES, fallback=True)
        return self._clean_values(df[column])

    def load_targets(self, excel_path: str | Path) -> list[dict]:
        """Load company, website and career URL records from an Excel workbook.

        Only the company column is required. Website/career columns are optional.
        Duplicate rows are removed using company + website + career URL.
        """
        df = self._read(excel_path)
        if df.empty or len(df.columns) == 0:
            return []

        company_col = self._resolve_column(df, None, self.COMPANY_COLUMN_NAMES, fallback=True)
        website_col = self._resolve_column(df, None, self.WEBSITE_COLUMN_NAMES)
        career_col = self._resolve_column(df, None, self.CAREER_COLUMN_NAMES)

        targets = []
        seen = set()
        for _, row in df.iterrows():
            company = self._clean_cell(row.get(company_col))
            if not company:
                continue
            website = self._clean_cell(row.get(website_col)) if website_col else ""
            career_url = self._clean_cell(row.get(career_col)) if career_col else ""
            key = (company.casefold(), website.casefold(), career_url.casefold())
            if key in seen:
                continue
            seen.add(key)
            targets.append({
                "company": company,
                "website": website or None,
                "career_url": career_url or None,
            })
        return targets

    @staticmethod
    def _read(excel_path: str | Path) -> pd.DataFrame:
        path = Path(excel_path)
        if not path.exists():
            raise FileNotFoundError(f"Company Excel file not found: {path}")
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError("CompanyLoader supports only .xlsx and .xls files")
        return pd.read_excel(path)

    def _resolve_company_column(self, df: pd.DataFrame, company_column: str | None) -> str:
        """Backward-compatible company-column resolver."""
        return self._resolve_column(
            df, company_column, self.COMPANY_COLUMN_NAMES, fallback=True
        )

    @staticmethod
    def _resolve_column(df, explicit, candidates, fallback=False):
        if explicit is not None:
            if explicit not in df.columns:
                raise ValueError(
                    f"Column '{explicit}' not found. Available columns: "
                    f"{', '.join(map(str, df.columns))}"
                )
            return explicit
        normalized = {str(column).strip().lower(): column for column in df.columns}
        for candidate in candidates:
            if candidate in normalized:
                return normalized[candidate]
        return df.columns[0] if fallback else None

    @staticmethod
    def _clean_cell(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    @classmethod
    def _clean_values(cls, series) -> list[str]:
        values = []
        seen = set()
        for value in series:
            cleaned = cls._clean_cell(value)
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                values.append(cleaned)
        return values
