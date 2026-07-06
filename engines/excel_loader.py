"""
Echo Registry Analyzer (ERA)
excel_loader.py
Version: 0.3.0
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
    def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
        df[config.COL_DATE] = pd.to_datetime(df[config.COL_DATE], errors="coerce")
        df[config.COL_BIRTHDAY] = pd.to_datetime(df[config.COL_BIRTHDAY], errors="coerce")
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
