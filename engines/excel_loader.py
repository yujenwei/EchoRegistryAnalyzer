"""
Echo Registry Analyzer (ERA)
excel_loader.py
Version: 0.4.3

Load and validate Excel files.

v0.4.3:
- Fix Excel serial number dates being parsed as 1970-01-01.
- Support mixed date formats including:
  - datetime objects
  - Excel serial numbers
  - YYYYMMDD numeric or string
  - general date strings
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

import config


class ExcelLoader:
    """Load and validate Excel files from input folder."""

    def __init__(self) -> None:
        self.files: List[Path] = []
        self.dataframes: List[pd.DataFrame] = []
        self.skipped_files: List[dict] = []

    def find_files(self) -> List[Path]:
        self.files = []
        for ext in config.SUPPORTED_EXTENSIONS:
            self.files.extend(config.INPUT_FOLDER.glob(f"*{ext}"))
        self.files = sorted(self.files)
        print(f"Searching in: {config.INPUT_FOLDER}")
        print(f"Found {len(self.files)} Excel files.")
        return self.files

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        new_cols = []
        for col in df.columns:
            col = str(col).strip()
            new_cols.append(config.COLUMN_ALIASES.get(col, col))
        df.columns = new_cols
        return df

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> list[str]:
        return [c for c in config.REQUIRED_COLUMNS if c not in df.columns]

    @staticmethod
    def normalize_mrn(df: pd.DataFrame) -> pd.DataFrame:
        df[config.COL_MRN] = (
            df[config.COL_MRN]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
        return df

    @staticmethod
    def parse_mixed_date(value):
        """Parse mixed date values safely.

        Why this function is needed:
        pandas.to_datetime(45000) may be interpreted as nanoseconds after
        1970-01-01, producing 1970-01-01. In Excel, 45000 usually means
        days after 1899-12-30. This function detects Excel serial dates first.
        """
        if pd.isna(value):
            return pd.NaT

        if isinstance(value, pd.Timestamp):
            return value

        # Python datetime/date objects are safely handled here.
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            return pd.to_datetime(value, errors="coerce")

        # Numeric values may be Excel serial dates or YYYYMMDD.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                number = float(value)
            except (TypeError, ValueError):
                return pd.NaT

            if pd.isna(number):
                return pd.NaT

            # YYYYMMDD numeric format, e.g. 20200131.
            if 19000101 <= int(number) <= 21001231:
                return pd.to_datetime(str(int(number)), format="%Y%m%d", errors="coerce")

            # Excel serial date. Typical valid range for clinical data.
            if 1 <= number <= 80000:
                return pd.to_datetime(number, unit="D", origin="1899-12-30", errors="coerce")

            return pd.to_datetime(value, errors="coerce")

        text = str(value).strip()
        if text == "" or text.lower() in {"nan", "none", "nat"}:
            return pd.NaT

        # Remove trailing .0 from values such as "20200131.0" or "45000.0".
        if text.endswith(".0"):
            text = text[:-2]

        # YYYYMMDD string.
        if text.isdigit() and len(text) == 8:
            return pd.to_datetime(text, format="%Y%m%d", errors="coerce")

        # Excel serial stored as string.
        if text.isdigit():
            number = int(text)
            if 1 <= number <= 80000:
                return pd.to_datetime(number, unit="D", origin="1899-12-30", errors="coerce")

        return pd.to_datetime(text, errors="coerce")

    @classmethod
    def normalize_dates(cls, df: pd.DataFrame) -> pd.DataFrame:
        df[config.COL_DATE] = df[config.COL_DATE].apply(cls.parse_mixed_date)
        df[config.COL_BIRTHDAY] = df[config.COL_BIRTHDAY].apply(cls.parse_mixed_date)
        return df

    def load(self) -> List[pd.DataFrame]:
        self.dataframes = []
        self.skipped_files = []

        for file in self.files:
            print(f"Reading {file.name}")
            try:
                df = pd.read_excel(file)
            except Exception as exc:
                self.skipped_files.append({"file": file.name, "reason": str(exc)})
                print(f"  Failed: {exc}")
                continue

            df = self.normalize_columns(df)
            missing = self.validate_columns(df)

            if missing:
                self.skipped_files.append({"file": file.name, "reason": f"Missing columns: {missing}"})
                print(f"  Missing columns: {missing}")
                continue

            df = self.normalize_mrn(df)
            df = self.normalize_dates(df)

            if config.KEEP_SOURCE_FILE:
                df[config.SOURCE_COLUMN] = file.name

            self.dataframes.append(df)
            print(f"  OK: {len(df)} rows")

        return self.dataframes
