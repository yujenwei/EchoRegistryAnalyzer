"""
Echo Registry Analyzer (ERA)
patient_engine.py
Version: 0.4.3

Create one-row-per-patient summary from merged_all.xlsx.
"""

from __future__ import annotations
from typing import Optional

import pandas as pd

import config
from engines.text_utils import clean_value, unique_join, normalize_text
from engines.excel_loader import ExcelLoader


class PatientEngine:
    """Build patient-level summary from examination-level merged data."""

    def __init__(self) -> None:
        self.df = pd.DataFrame()
        self.patient_df = pd.DataFrame()
        self.birthday_conflict_df = pd.DataFrame()
        self.gender_conflict_df = pd.DataFrame()
        self.data_quality_df = pd.DataFrame()

    @staticmethod
    def latest_non_empty(series: pd.Series) -> str:
        """Return latest non-empty value in a date-sorted group."""
        for value in reversed(series.tolist()):
            text = clean_value(value)
            if text:
                return text
        return ""

    @staticmethod
    def most_common_non_empty(series: pd.Series) -> object:
        """Return most frequent non-empty value; fallback empty string."""
        cleaned = []
        for value in series:
            if pd.isna(value):
                continue
            cleaned.append(value)
        if not cleaned:
            return ""
        s = pd.Series(cleaned)
        mode = s.mode(dropna=True)
        if len(mode) > 0:
            return mode.iloc[0]
        return cleaned[-1]

    @staticmethod
    def extract_lvef_values(text: str) -> list[float]:
        """Extract all LVEF/EF numeric values from free text."""
        if not text:
            return []
        values = []
        for match in config.LVEF_PATTERN.finditer(str(text)):
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if 0 < value <= 100:
                values.append(value)
        return values

    def load(self) -> None:
        infile = config.OUTPUT_FOLDER / config.MERGED_FILE
        if not infile.exists():
            raise FileNotFoundError(
                f"{infile} not found. Please run MergeEngine first."
            )

        self.df = pd.read_excel(infile, dtype={config.COL_MRN: str})
        self.df[config.COL_DATE] = self.df[config.COL_DATE].apply(ExcelLoader.parse_mixed_date)
        self.df[config.COL_BIRTHDAY] = self.df[config.COL_BIRTHDAY].apply(ExcelLoader.parse_mixed_date)
        self.df[config.COL_MRN] = (
            self.df[config.COL_MRN]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
        self.df = self.df.sort_values([config.COL_MRN, config.COL_DATE])

    def build_patient_summary(self) -> None:
        records = []

        for mrn, group in self.df.groupby(config.COL_MRN, dropna=False):
            group = group.sort_values(config.COL_DATE)

            diagnosis_text = unique_join(group[config.COL_DIAGNOSIS], config.TEXT_SEPARATOR)
            report_text = unique_join(group[config.COL_REPORT], config.TEXT_SEPARATOR)
            full_text = normalize_text(f"{diagnosis_text} {report_text}")

            lvef_values = self.extract_lvef_values(full_text)
            lowest_lvef: Optional[float] = min(lvef_values) if lvef_values else None

            record = {
                config.COL_MRN: mrn,
                config.COL_NAME: self.latest_non_empty(group[config.COL_NAME]),
                config.COL_GENDER: self.latest_non_empty(group[config.COL_GENDER]),
                config.COL_BIRTHDAY: self.most_common_non_empty(group[config.COL_BIRTHDAY]),
                "第一次檢查日期": group[config.COL_DATE].min(),
                "最後一次檢查日期": group[config.COL_DATE].max(),
                "檢查次數": len(group),
                config.COL_EXAM: unique_join(group[config.COL_EXAM], config.TEXT_SEPARATOR),
                config.COL_DIAGNOSIS: diagnosis_text,
                config.COL_REPORT: report_text,
                config.FULL_TEXT_COL: full_text,
                config.LOWEST_LVEF_COL: lowest_lvef,
                config.HAS_LVEF_LT_50_COL: bool(
                    lowest_lvef is not None and lowest_lvef < config.LVEF_THRESHOLD
                ),
            }

            if config.SOURCE_COLUMN in group.columns:
                record[config.SOURCE_COLUMN] = unique_join(
                    group[config.SOURCE_COLUMN], config.TEXT_SEPARATOR
                )

            records.append(record)

        self.patient_df = pd.DataFrame(records)

    def detect_birthday_conflicts(self) -> None:
        records = []

        for mrn, group in self.df.groupby(config.COL_MRN, dropna=False):
            values = (
                group[config.COL_BIRTHDAY]
                .dropna()
                .dt.strftime("%Y-%m-%d")
                .unique()
                .tolist()
            )
            if len(values) > 1:
                records.append({
                    config.COL_MRN: mrn,
                    "出生日期種類數": len(values),
                    "出生日期清單": config.TEXT_SEPARATOR.join(values),
                    "檢查次數": len(group),
                })

        self.birthday_conflict_df = pd.DataFrame(records)

    def detect_gender_conflicts(self) -> None:
        records = []

        for mrn, group in self.df.groupby(config.COL_MRN, dropna=False):
            values = []
            for value in group[config.COL_GENDER]:
                text = clean_value(value)
                if text and text not in values:
                    values.append(text)

            if len(values) > 1:
                records.append({
                    config.COL_MRN: mrn,
                    "性別種類數": len(values),
                    "性別清單": config.TEXT_SEPARATOR.join(values),
                    "檢查次數": len(group),
                })

        self.gender_conflict_df = pd.DataFrame(records)

    def build_data_quality_report(self) -> None:
        rows = [
            {"項目": "總檢查筆數", "數量": len(self.df)},
            {"項目": "病人數", "數量": self.df[config.COL_MRN].nunique()},
            {"項目": "缺少病歷號碼", "數量": int((self.df[config.COL_MRN] == "").sum())},
            {"項目": "缺少檢查日期", "數量": int(self.df[config.COL_DATE].isna().sum())},
            {"項目": "缺少出生日期", "數量": int(self.df[config.COL_BIRTHDAY].isna().sum())},
            {"項目": "缺少診斷", "數量": int(self.df[config.COL_DIAGNOSIS].isna().sum())},
            {"項目": "缺少報告", "數量": int(self.df[config.COL_REPORT].isna().sum())},
            {"項目": "出生日期衝突病人數", "數量": len(self.birthday_conflict_df)},
            {"項目": "性別衝突病人數", "數量": len(self.gender_conflict_df)},
            {"項目": "LVEF < 50 病人數", "數量": int(self.patient_df[config.HAS_LVEF_LT_50_COL].sum())},
        ]
        self.data_quality_df = pd.DataFrame(rows)

    def export(self) -> None:
        patient_file = config.OUTPUT_FOLDER / config.PATIENT_FILE
        birthday_file = config.OUTPUT_FOLDER / config.BIRTHDAY_CONFLICT_FILE
        gender_file = config.OUTPUT_FOLDER / config.GENDER_CONFLICT_FILE
        quality_file = config.OUTPUT_FOLDER / config.DATA_QUALITY_FILE

        self.patient_df.to_excel(patient_file, index=False)
        self.birthday_conflict_df.to_excel(birthday_file, index=False)
        self.gender_conflict_df.to_excel(gender_file, index=False)
        self.data_quality_df.to_excel(quality_file, index=False)

        print()
        print("Patient summary completed.")
        print(f"Saved: {patient_file}")
        print(f"Saved: {birthday_file}")
        print(f"Saved: {gender_file}")
        print(f"Saved: {quality_file}")

    def run(self) -> pd.DataFrame:
        self.load()
        self.build_patient_summary()
        self.detect_birthday_conflicts()
        self.detect_gender_conflicts()
        self.build_data_quality_report()
        self.export()
        return self.patient_df
