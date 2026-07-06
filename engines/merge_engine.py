"""
Echo Registry Analyzer (ERA)
merge_engine.py
Version: 0.3.0
"""

from __future__ import annotations
import pandas as pd

import config
from engines.excel_loader import ExcelLoader


class MergeEngine:
    """Merge all yearly Excel files into one examination-level table."""

    def __init__(self) -> None:
        self.loader = ExcelLoader()
        self.merged_df = pd.DataFrame()

    def run(self) -> pd.DataFrame:
        self.loader.find_files()
        dfs = self.loader.load()

        if not dfs:
            print("No valid Excel data found.")
            self.merged_df = pd.DataFrame()
            return self.merged_df

        self.merged_df = pd.concat(dfs, ignore_index=True)

        before = len(self.merged_df)
        if config.REMOVE_DUPLICATE_ROWS:
            self.merged_df = self.merged_df.drop_duplicates()
        after = len(self.merged_df)

        if config.SORT_BY_DATE:
            self.merged_df = self.merged_df.sort_values(config.COL_DATE)

        outfile = config.OUTPUT_FOLDER / config.MERGED_FILE
        self.merged_df.to_excel(outfile, index=False)

        print()
        print("Merge completed.")
        print(f"Rows before duplicate removal: {before}")
        print(f"Rows after duplicate removal: {after}")
        print(f"Saved: {outfile}")

        return self.merged_df
