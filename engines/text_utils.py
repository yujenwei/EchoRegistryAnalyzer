"""
Echo Registry Analyzer (ERA)
text_utils.py
Version: 0.3.0
"""

from __future__ import annotations
import re
from typing import Iterable, List


def normalize_text(text: object) -> str:
    """Normalize free text for keyword searching."""
    if text is None:
        return ""
    text = str(text).lower()
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_value(value: object) -> str:
    """Convert one cell value to clean string."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat"}:
        return ""
    return text


def unique_join(values: Iterable[object], separator: str = " / ") -> str:
    """Join non-empty unique values while preserving order."""
    result: List[str] = []
    for value in values:
        text = clean_value(value)
        if text and text not in result:
            result.append(text)
    return separator.join(result)


def join_all(values: Iterable[object], separator: str = " / ") -> str:
    """Join all non-empty values while preserving repetitions."""
    result: List[str] = []
    for value in values:
        text = clean_value(value)
        if text:
            result.append(text)
    return separator.join(result)
