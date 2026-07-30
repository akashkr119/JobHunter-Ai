"""Load company names from Excel files."""

from pathlib import Path
import pandas as pd


class CompanyLoader:
    """Loads company names from an Excel file."""

    def load(self, excel_path: str | Path) -> list[str]:
        df = pd.read_excel(excel_path)
        if df.empty:
            return []

        first_column = df.columns[0]
        return (
            df[first_column]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
