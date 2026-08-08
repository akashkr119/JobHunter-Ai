"""Load, enrich, and persist company targets from Excel files."""

from pathlib import Path

import pandas as pd


class CompanyLoader:
    """Load company names and maintain the user's company workbook."""

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
    STATUS_COLUMN_NAMES = ("discovery status", "discovery_status", "status")
    CHECKED_COLUMN_NAMES = ("last checked", "last_checked", "discovery checked")

    def load(self, excel_path: str | Path, company_column: str | None = None) -> list[str]:
        """Return unique company names, preserving the original public API."""
        df = self._read(excel_path)
        if df.empty or len(df.columns) == 0:
            return []
        column = self._resolve_column(df, company_column, self.COMPANY_COLUMN_NAMES, fallback=True)
        return self._clean_values(df[column])

    def load_targets(self, excel_path: str | Path) -> list[dict]:
        """Load company, website and career URL records from an Excel workbook.

        A company name is the only required field. Website and Career URL are
        optional and may be populated later by the automatic discovery stage.
        """
        df = self._read(excel_path)
        if df.empty or len(df.columns) == 0:
            return []

        company_col = self._resolve_column(df, None, self.COMPANY_COLUMN_NAMES, fallback=True)
        website_col = self._resolve_column(df, None, self.WEBSITE_COLUMN_NAMES)
        career_col = self._resolve_column(df, None, self.CAREER_COLUMN_NAMES)

        targets = []
        seen = set()
        for index, row in df.iterrows():
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
                "row_index": int(index),
            })
        return targets

    def update_discovery_results(self, excel_path: str | Path, results: dict[str, dict]) -> None:
        """Write discovered URLs/status back into the same user Excel workbook.

        Existing user columns are preserved. Discovery columns are added only
        when necessary and are explicitly converted to object/string-friendly
        dtype so an empty Excel column loaded as float64 can accept URLs.
        """
        path = Path(excel_path)
        df = self._read(path).copy()
        if df.empty:
            return

        company_col = self._resolve_column(df, None, self.COMPANY_COLUMN_NAMES, fallback=True)
        website_col = self._resolve_column(df, None, self.WEBSITE_COLUMN_NAMES)
        career_col = self._resolve_column(df, None, self.CAREER_COLUMN_NAMES)
        status_col = self._resolve_column(df, None, self.STATUS_COLUMN_NAMES)
        checked_col = self._resolve_column(df, None, self.CHECKED_COLUMN_NAMES)

        if website_col is None:
            website_col = "Website"
            df[website_col] = pd.Series([""] * len(df), index=df.index, dtype="object")
        else:
            df[website_col] = df[website_col].astype("object")

        if career_col is None:
            career_col = "Career URL"
            df[career_col] = pd.Series([""] * len(df), index=df.index, dtype="object")
        else:
            df[career_col] = df[career_col].astype("object")

        if status_col is None:
            status_col = "Discovery Status"
            df[status_col] = pd.Series([""] * len(df), index=df.index, dtype="object")
        else:
            df[status_col] = df[status_col].astype("object")

        if checked_col is None:
            checked_col = "Last Checked"
            df[checked_col] = pd.Series([""] * len(df), index=df.index, dtype="object")
        else:
            df[checked_col] = df[checked_col].astype("object")

        normalized = {str(key).strip().casefold(): value for key, value in results.items()}
        for index, value in df[company_col].items():
            company = self._clean_cell(value)
            result = normalized.get(company.casefold())
            if not result:
                continue
            if result.get("website"):
                df.at[index, website_col] = str(result["website"])
            if result.get("career_url"):
                df.at[index, career_col] = str(result["career_url"])
            if result.get("status") is not None:
                df.at[index, status_col] = str(result["status"])
            if result.get("checked_at"):
                df.at[index, checked_col] = str(result["checked_at"])

        df.to_excel(path, index=False)

    @staticmethod
    def _read(excel_path: str | Path) -> pd.DataFrame:
        path = Path(excel_path)
        if not path.exists():
            raise FileNotFoundError(f"Company Excel file not found: {path}")
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError("CompanyLoader supports only .xlsx and .xls files")
        return pd.read_excel(path)

    def _resolve_company_column(self, df: pd.DataFrame, company_column: str | None) -> str:
        return self._resolve_column(df, company_column, self.COMPANY_COLUMN_NAMES, fallback=True)

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
