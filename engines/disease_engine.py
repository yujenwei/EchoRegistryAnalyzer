"""
Echo Registry Analyzer (ERA)
disease_engine.py
Version: 0.4.3

Optimized disease classification.

v0.4.2:
- Pre-groups examination rows by MRN to avoid repeated DataFrame filtering.
- Prints progress during disease classification.
- Keeps row-level negation detection:
  - "no PDA" does not count as PDA.
  - Previous positive PDA is still counted even if later reports say "no PDA".
"""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

import config
from engines.text_utils import normalize_text
from engines.excel_loader import ExcelLoader


class DiseaseEngine:
    """Create disease summary and disease-specific Excel reports."""

    def __init__(self) -> None:
        self.patient_df = pd.DataFrame()
        self.exam_df = pd.DataFrame()
        self.exam_text_by_mrn: dict[str, list[tuple[str, str]]] = {}
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

        self.patient_df[config.COL_MRN] = (
            self.patient_df[config.COL_MRN]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

        self.patient_df[config.FULL_TEXT_COL] = (
            self.patient_df[config.FULL_TEXT_COL]
            .fillna("")
            .astype(str)
            .map(normalize_text)
        )

    def load_exam_data(self) -> None:
        """Load examination-level merged data for row-level disease matching."""
        infile = config.OUTPUT_FOLDER / config.MERGED_FILE
        if not infile.exists():
            raise FileNotFoundError(
                f"{infile} not found. Please run MergeEngine first."
            )

        self.exam_df = pd.read_excel(infile, dtype={config.COL_MRN: str})

        self.exam_df[config.COL_MRN] = (
            self.exam_df[config.COL_MRN]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

        self.exam_df[config.COL_DATE] = self.exam_df[config.COL_DATE].apply(ExcelLoader.parse_mixed_date)

        diagnosis = self.exam_df[config.COL_DIAGNOSIS].fillna("").astype(str)
        report = self.exam_df[config.COL_REPORT].fillna("").astype(str)

        self.exam_df["_era_exam_text"] = (diagnosis + " " + report).map(normalize_text)

        self.build_exam_index()

    def build_exam_index(self) -> None:
        """Pre-group exam text by MRN for fast disease classification."""
        self.exam_text_by_mrn = {}

        for mrn, group in self.exam_df.groupby(config.COL_MRN, dropna=False):
            entries: list[tuple[str, str]] = []

            for _, row in group.iterrows():
                exam_date = row.get(config.COL_DATE)
                if pd.notna(exam_date):
                    date_text = pd.to_datetime(exam_date).strftime("%Y-%m-%d")
                else:
                    date_text = "unknown date"

                text = row.get("_era_exam_text", "")
                entries.append((date_text, text))

            self.exam_text_by_mrn[str(mrn).strip()] = entries

    def load_disease_rules(self) -> None:
        infile = config.DISEASE_DICTIONARY_FILE
        if not infile.exists():
            raise FileNotFoundError(f"Disease dictionary not found: {infile}")

        with open(infile, "r", encoding="utf-8") as f:
            self.disease_rules = json.load(f)

    @staticmethod
    def keyword_pattern(keyword: str) -> re.Pattern:
        """Build a keyword regex with safer boundaries for abbreviations."""
        keyword = normalize_text(keyword)
        escaped = re.escape(keyword)

        if len(keyword.replace(" ", "")) <= 4 and re.fullmatch(r"[a-z0-9 ]+", keyword):
            return re.compile(
                rf"(?<![a-z0-9]){escaped}(?![a-z0-9])",
                re.IGNORECASE,
            )

        return re.compile(escaped, re.IGNORECASE)

    def build_keyword_patterns(self, keywords: list[str]) -> list[tuple[str, re.Pattern]]:
        """Compile keyword patterns once per disease."""
        patterns = []
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)
            if not keyword_norm:
                continue
            patterns.append((keyword, self.keyword_pattern(keyword_norm)))
        return patterns

    @staticmethod
    def _keyword_variants(keyword: str) -> list[str]:
        keyword = normalize_text(keyword)
        variants = [keyword]

        if len(keyword) <= 4 and " " not in keyword:
            dotted = ".".join(list(keyword)) + "."
            variants.append(dotted)

        return list(dict.fromkeys(variants))

    def is_negated_match(self, text: str, keyword: str, start: int, end: int) -> bool:
        """Determine whether a matched keyword is locally negated."""
        text = normalize_text(text)
        keyword = normalize_text(keyword)

        local = text[max(0, start - 80):min(len(text), end + 80)].strip()
        before = text[max(0, start - 80):start].strip()

        variants = self._keyword_variants(keyword)

        for kw in variants:
            kw_escaped = re.escape(kw)

            prefix_patterns = [
                rf"\bno\s+{kw_escaped}\b",
                rf"\bno\s+evidence\s+of\s+{kw_escaped}\b",
                rf"\bwithout\s+{kw_escaped}\b",
                rf"\babsence\s+of\s+{kw_escaped}\b",
                rf"\bnegative\s+for\s+{kw_escaped}\b",
                rf"\bfree\s+of\s+{kw_escaped}\b",
                rf"\brule\s+out\s+{kw_escaped}\b",
                rf"\br/o\s+{kw_escaped}\b",
                rf"\bexclude\s+{kw_escaped}\b",
                rf"\bexcluded\s+{kw_escaped}\b",
            ]

            suffix_patterns = [
                rf"\b{kw_escaped}\s+absent\b",
                rf"\b{kw_escaped}\s+excluded\b",
                rf"\b{kw_escaped}\s+negative\b",
                rf"\b{kw_escaped}\s+not\s+seen\b",
                rf"\b{kw_escaped}\s+not\s+found\b",
            ]

            for pattern in prefix_patterns + suffix_patterns:
                if re.search(pattern, local, flags=re.IGNORECASE):
                    return True

        before_words = re.findall(r"[a-z0-9/]+", before)
        last_words = " ".join(before_words[-6:])

        generic_prefixes = [
            "no",
            "without",
            "absence of",
            "negative for",
            "no evidence of",
            "rule out",
            "r/o",
        ]

        for neg in generic_prefixes:
            if neg in last_words:
                return True

        return False

    def has_explicit_exclusion(self, text: str, exclude_terms: list[str]) -> bool:
        """Check explicit exclusion phrases from diseases.json."""
        text = normalize_text(text)
        for term in exclude_terms:
            term = normalize_text(term)
            if term and term in text:
                return True
        return False

    def match_keywords_in_exam_text(
        self,
        text: str,
        keyword_patterns: list[tuple[str, re.Pattern]],
        exclude_terms: list[str] | None = None,
    ) -> list[str]:
        """Return non-negated matched keywords in one examination text."""
        text = normalize_text(text)

        if exclude_terms and self.has_explicit_exclusion(text, exclude_terms):
            return []

        matches: list[str] = []

        for keyword, pattern in keyword_patterns:
            keyword_norm = normalize_text(keyword)

            for match in pattern.finditer(text):
                if not self.is_negated_match(
                    text=text,
                    keyword=keyword_norm,
                    start=match.start(),
                    end=match.end(),
                ):
                    matches.append(keyword)
                    break

        return matches

    def match_lvef_rule(self, patient_row: pd.Series, threshold: float | int | None) -> bool:
        if threshold is None:
            return False

        if config.LOWEST_LVEF_COL not in patient_row.index:
            return False

        value = patient_row.get(config.LOWEST_LVEF_COL)
        if pd.isna(value):
            return False

        try:
            return float(value) < float(threshold)
        except (TypeError, ValueError):
            return False

    def classify_patient_by_exam_rows(
        self,
        mrn: str,
        keyword_patterns: list[tuple[str, re.Pattern]],
        exclude_terms: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Classify a patient using pre-grouped examination rows."""
        patient_exams = self.exam_text_by_mrn.get(str(mrn).strip(), [])
        positive_reasons: list[str] = []

        for date_text, text in patient_exams:
            matched = self.match_keywords_in_exam_text(text, keyword_patterns, exclude_terms)

            if matched:
                positive_reasons.append(
                    f"{date_text}: keyword: {', '.join(matched)}"
                )

        if positive_reasons:
            return True, " | ".join(positive_reasons)

        return False, ""

    def classify(self) -> None:
        summary = self.patient_df.copy()
        total_diseases = len(self.disease_rules)

        print()
        print("Starting disease classification...")
        print(f"Patients: {len(self.patient_df)}")
        print(f"Diseases: {total_diseases}")

        for idx, (disease_name, rule) in enumerate(self.disease_rules.items(), start=1):
            print(f"[{idx}/{total_diseases}] Classifying: {disease_name}")

            flags = []
            reasons = []
            keyword_patterns = self.build_keyword_patterns(rule.get("keywords", []))
            exclude_terms = rule.get("exclude", [])

            for _, patient_row in self.patient_df.iterrows():
                mrn = str(patient_row.get(config.COL_MRN, "")).strip()

                keyword_matched, keyword_reason = self.classify_patient_by_exam_rows(
                    mrn=mrn,
                    keyword_patterns=keyword_patterns,
                    exclude_terms=exclude_terms,
                )

                lvef_threshold = rule.get("lvef_less_than")
                lvef_matched = self.match_lvef_rule(patient_row, lvef_threshold)

                matched_reasons = []

                if keyword_matched:
                    matched_reasons.append(keyword_reason)

                if lvef_matched:
                    matched_reasons.append(f"LVEF < {lvef_threshold}")

                flags.append(bool(matched_reasons))
                reasons.append(" | ".join(matched_reasons))

            summary[disease_name] = flags
            summary[f"{disease_name}__reason"] = reasons

        self.disease_summary_df = summary

    @staticmethod
    def safe_filename(name: str) -> str:
        name = name.replace("/", "_")
        name = re.sub(r"[^\w\-. ]+", "_", name)
        name = name.strip().replace(" ", "_")
        return f"{name}.xlsx"

    def export(self) -> None:
        config.DISEASE_OUTPUT_FOLDER.mkdir(exist_ok=True)

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

        for disease_name in self.disease_rules.keys():
            matched = self.disease_summary_df[
                self.disease_summary_df[disease_name] == True
            ].copy()

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
        self.load_exam_data()
        self.load_disease_rules()
        self.classify()
        self.export()
        return self.disease_summary_df
