"""Load company names from Excel files."""

from pathlib import Path

import pandas as pd


class CompanyLoader:
    """Load unique company names from an Excel workbook."""

    COMPANY_COLUMN_NAMES = (
        "company",
        "company name",
        "company_name",
        "organization",
        "organisation",
    )

    def load(
        self,
        excel_path: str | Path,
        company_column: str | None = None,
    ) -> list[str]:
        """Return unique, non-empty company names from an Excel file.

        If ``company_column`` is not supplied, common company-column names are
        detected case-insensitively. For backward compatibility, the first
        column is used when no known company column is present.
        """
        path = Path(excel_path)

        if not path.exists():
            raise FileNotFoundError(f"Company Excel file not found: {path}")

        if path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError("CompanyLoader supports only .xlsx and .xls files")

        df = pd.read_excel(path)
        if df.empty or len(df.columns) == 0:
            return []

        column = self._resolve_company_column(df, company_column)

        return (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda values: values.ne("")]
            .drop_duplicates()
            .tolist()
        )

    def _resolve_company_column(
        self,
        df: pd.DataFrame,
        company_column: str | None,
    ) -> str:
        """Resolve the column containing company names."""
        if company_column is not None:
            if company_column not in df.columns:
                raise ValueError(
                    f"Company column '{company_column}' not found. "
                    f"Available columns: {', '.join(map(str, df.columns))}"
                )
            return company_column

        normalized_columns = {
            str(column).strip().lower(): column for column in df.columns
        }
        for candidate in self.COMPANY_COLUMN_NAMES:
            if candidate in normalized_columns:
                return normalized_columns[candidate]

        return df.columns[0]
