"""
Echo Registry Analyzer (ERA)
disease_engine.py
Version: 0.4.0

Classify patients into disease groups using dictionary/diseases.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

import config
from engines.text_utils import normalize_text


class DiseaseEngine:
    """Create disease summary and disease-specific Excel reports."""

    def __init__(self) -> None:
        self.patient_df = pd.DataFrame()
        self.disease_rules: dict[str, dict[str, Any]] = {}
        self.disease_summary_df = pd.DataFrame()

    def load_patient_summary(self) -> None:
        infile = config.OUTPUT_FOLDER / config.PATIENT_FILE
        if not infile.exists():
            raise FileNotFoundError(
                f"{infile} not found. Please run PatientEngine first."
            )

        self.patient_df = pd.read_excel(infile, dtype={config.COL_MRN: str})

        if config.FULL_TEXT_COL not in self.patient_df.columns:
            raise ValueError(
                f"Missing column: {config.FULL_TEXT_COL}. "
                "Please regenerate patient_summary.xlsx with PatientEngine v0.3+."
            )

        self.patient_df[config.FULL_TEXT_COL] = (
            self.patient_df[config.FULL_TEXT_COL]
            .fillna("")
            .astype(str)
            .map(normalize_text)
        )

    def load_disease_rules(self) -> None:
        infile = config.DISEASE_DICTIONARY_FILE
        if not infile.exists():
            raise FileNotFoundError(f"Disease dictionary not found: {infile}")

        with open(infile, "r", encoding="utf-8") as f:
            self.disease_rules = json.load(f)

    @staticmethod
    def keyword_pattern(keyword: str) -> re.Pattern:
        """Build a keyword regex with safer boundaries for abbreviations."""
        keyword = keyword.strip()
        escaped = re.escape(keyword)

        # For short uppercase-like abbreviations after normalization, require boundaries.
        if len(keyword) <= 4 and re.fullmatch(r"[A-Za-z0-9 ]+", keyword):
            return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)

        return re.compile(escaped, re.IGNORECASE)

    def has_exclusion(self, text: str, exclude_terms: list[str]) -> bool:
        """Return True if text contains explicit exclusion phrase."""
        for term in exclude_terms:
            term = normalize_text(term)
            if term and term in text:
                return True
        return False

    def match_keywords(self, text: str, keywords: list[str]) -> list[str]:
        """Return matched keywords."""
        matches = []
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)
            if not keyword_norm:
                continue
            pattern = self.keyword_pattern(keyword_norm)
            if pattern.search(text):
                matches.append(keyword)
        return matches

    def match_lvef_rule(self, row: pd.Series, threshold: float | int | None) -> bool:
        """Check LVEF threshold rule from patient summary."""
        if threshold is None:
            return False

        if config.LOWEST_LVEF_COL not in row.index:
            return False

        value = row.get(config.LOWEST_LVEF_COL)
        if pd.isna(value):
            return False

        try:
            return float(value) < float(threshold)
        except (TypeError, ValueError):
            return False

    def classify_one_patient(
        self,
        row: pd.Series,
        disease_name: str,
        rule: dict[str, Any],
    ) -> tuple[bool, str]:
        """Classify one patient for one disease."""
        text = normalize_text(row.get(config.FULL_TEXT_COL, ""))

        exclude_terms = rule.get("exclude", [])
        if self.has_exclusion(text, exclude_terms):
            return False, "excluded"

        keywords = rule.get("keywords", [])
        matched_keywords = self.match_keywords(text, keywords)

        lvef_threshold = rule.get("lvef_less_than")
        lvef_matched = self.match_lvef_rule(row, lvef_threshold)

        matched_reasons = []

        if matched_keywords:
            matched_reasons.append("keyword: " + ", ".join(matched_keywords))

        if lvef_matched:
            matched_reasons.append(f"LVEF < {lvef_threshold}")

        return bool(matched_reasons), " | ".join(matched_reasons)

    @staticmethod
    def safe_filename(name: str) -> str:
        """Create a safe Excel filename from disease name."""
        name = name.replace("/", "_")
        name = re.sub(r"[^\w\-. ]+", "_", name)
        name = name.strip().replace(" ", "_")
        return f"{name}.xlsx"

    def classify(self) -> None:
        summary = self.patient_df.copy()

        for disease_name, rule in self.disease_rules.items():
            flags = []
            reasons = []

            for _, row in self.patient_df.iterrows():
                matched, reason = self.classify_one_patient(row, disease_name, rule)
                flags.append(bool(matched))
                reasons.append(reason if matched else "")

            summary[disease_name] = flags
            summary[f"{disease_name}__reason"] = reasons

        self.disease_summary_df = summary

    def export(self) -> None:
        config.DISEASE_OUTPUT_FOLDER.mkdir(exist_ok=True)

        # Export compact disease summary
        base_cols = [
            config.COL_MRN,
            config.COL_NAME,
            config.COL_GENDER,
            config.COL_BIRTHDAY,
            "第一次檢查日期",
            "最後一次檢查日期",
            "檢查次數",
            config.LOWEST_LVEF_COL,
            config.HAS_LVEF_LT_50_COL,
        ]
        base_cols = [c for c in base_cols if c in self.disease_summary_df.columns]

        disease_cols = list(self.disease_rules.keys())
        compact = self.disease_summary_df[base_cols + disease_cols].copy()

        summary_file = config.OUTPUT_FOLDER / config.DISEASE_FILE
        compact.to_excel(summary_file, index=False)

        # Export one file per disease
        for disease_name in self.disease_rules.keys():
            matched = self.disease_summary_df[self.disease_summary_df[disease_name] == True].copy()

            reason_col = f"{disease_name}__reason"
            if reason_col in matched.columns:
                matched[config.DISEASE_MATCH_DETAIL_COL] = matched[reason_col]

            export_cols = [
                config.COL_MRN,
                config.COL_NAME,
                config.COL_GENDER,
                config.COL_BIRTHDAY,
                "第一次檢查日期",
                "最後一次檢查日期",
                "檢查次數",
                config.COL_DIAGNOSIS,
                config.COL_REPORT,
                config.LOWEST_LVEF_COL,
                config.HAS_LVEF_LT_50_COL,
                config.DISEASE_MATCH_DETAIL_COL,
                config.SOURCE_COLUMN,
            ]
            export_cols = [c for c in export_cols if c in matched.columns]

            outfile = config.DISEASE_OUTPUT_FOLDER / self.safe_filename(disease_name)
            matched[export_cols].to_excel(outfile, index=False)

        print()
        print("Disease classification completed.")
        print(f"Saved: {summary_file}")
        print(f"Saved disease reports to: {config.DISEASE_OUTPUT_FOLDER}")

    def run(self) -> pd.DataFrame:
        self.load_patient_summary()
        self.load_disease_rules()
        self.classify()
        self.export()
        return self.disease_summary_df
