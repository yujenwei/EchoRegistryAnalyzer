"""
Echo Registry Analyzer (ERA)
config.py
Version: 0.3.0
"""

from pathlib import Path
import re

VERSION = "0.3.0"

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_FOLDER = PROJECT_ROOT / "input"
OUTPUT_FOLDER = PROJECT_ROOT / "output"
LOG_FOLDER = PROJECT_ROOT / "logs"
DICTIONARY_FOLDER = PROJECT_ROOT / "dictionary"

for folder in (INPUT_FOLDER, OUTPUT_FOLDER, LOG_FOLDER, DICTIONARY_FOLDER):
    folder.mkdir(exist_ok=True)

SUPPORTED_EXTENSIONS = [".xlsx", ".xls"]

COL_DATE = "檢查日期"
COL_MRN = "病歷號碼"
COL_NAME = "姓名"
COL_GENDER = "性別"
COL_BIRTHDAY = "出生日期"
COL_EXAM = "檢查項目"
COL_DIAGNOSIS = "診斷"
COL_REPORT = "報告"

COLUMN_ALIASES = {
    "檢查日期": COL_DATE, "檢查時間": COL_DATE, "Date": COL_DATE, "date": COL_DATE,
    "病歷號": COL_MRN, "病歷號碼": COL_MRN, "MRN": COL_MRN, "mrn": COL_MRN,
    "姓名": COL_NAME, "Name": COL_NAME, "name": COL_NAME,
    "性別": COL_GENDER, "Gender": COL_GENDER, "gender": COL_GENDER,
    "出生日期": COL_BIRTHDAY, "生日": COL_BIRTHDAY, "Birthday": COL_BIRTHDAY,
    "檢查項目": COL_EXAM, "Exam": COL_EXAM,
    "診斷": COL_DIAGNOSIS, "Diagnosis": COL_DIAGNOSIS,
    "報告": COL_REPORT, "檢查發現": COL_REPORT, "Finding": COL_REPORT, "Report": COL_REPORT,
}

REQUIRED_COLUMNS = [
    COL_DATE, COL_MRN, COL_NAME, COL_GENDER,
    COL_BIRTHDAY, COL_EXAM, COL_DIAGNOSIS, COL_REPORT
]

TEXT_SEPARATOR = " / "
KEEP_SOURCE_FILE = True
SOURCE_COLUMN = "來源檔案"
REMOVE_DUPLICATE_ROWS = True
SORT_BY_DATE = True

MERGED_FILE = "merged_all.xlsx"
PATIENT_FILE = "patient_summary.xlsx"
DISEASE_FILE = "disease_summary.xlsx"
BIRTHDAY_CONFLICT_FILE = "birthday_conflict.xlsx"
GENDER_CONFLICT_FILE = "gender_conflict.xlsx"
DATA_QUALITY_FILE = "data_quality.xlsx"

FULL_TEXT_COL = "全文"
LOWEST_LVEF_COL = "最低LVEF"
HAS_LVEF_LT_50_COL = "LVEF小於50"

LVEF_THRESHOLD = 50
LVEF_PATTERN = re.compile(
    r"(?:LVEF|LV\s*EF|EF|Ejection\s*Fraction)"
    r"\s*(?:is|was|約|about|around|approximately)?\s*"
    r"[:=]?\s*"
    r"(\d{1,3})"
    r"\s*(?:%|percent)?",
    flags=re.IGNORECASE
)

NEGATION_WORDS = [
    "no", "without", "rule out", "r/o", "exclude", "excluded",
    "unlikely", "absence of", "negative for", "no evidence of"
]

LOG_FILE = LOG_FOLDER / "ERA.log"
