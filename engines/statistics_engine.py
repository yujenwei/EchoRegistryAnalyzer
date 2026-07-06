"""
Echo Registry Analyzer (ERA)
statistics_engine.py
Version: 0.4.0
"""

from __future__ import annotations

import pandas as pd

import config


class StatisticsEngine:
    """Create simple disease count statistics."""

    def __init__(self) -> None:
        self.disease_summary_df = pd.DataFrame()
        self.statistics_df = pd.DataFrame()

    def load(self) -> None:
        infile = config.OUTPUT_FOLDER / config.DISEASE_FILE
        if not infile.exists():
            raise FileNotFoundError(
                f"{infile} not found. Please run DiseaseEngine first."
            )
        self.disease_summary_df = pd.read_excel(infile, dtype={config.COL_MRN: str})

    def build(self) -> None:
        known_base_cols = {
            config.COL_MRN,
            config.COL_NAME,
            config.COL_GENDER,
            config.COL_BIRTHDAY,
            "第一次檢查日期",
            "最後一次檢查日期",
            "檢查次數",
            config.LOWEST_LVEF_COL,
            config.HAS_LVEF_LT_50_COL,
        }

        rows = [
            {"項目": "病人數", "數量": len(self.disease_summary_df)}
        ]

        for col in self.disease_summary_df.columns:
            if col in known_base_cols:
                continue
            if self.disease_summary_df[col].dropna().isin([True, False]).all():
                rows.append({
                    "項目": col,
                    "數量": int(self.disease_summary_df[col].fillna(False).sum())
                })

        self.statistics_df = pd.DataFrame(rows)

    def export(self) -> None:
        outfile = config.OUTPUT_FOLDER / "disease_statistics.xlsx"
        self.statistics_df.to_excel(outfile, index=False)
        print(f"Saved: {outfile}")

    def run(self) -> pd.DataFrame:
        self.load()
        self.build()
        self.export()
        return self.statistics_df
