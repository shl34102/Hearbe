"""
Selection intent helpers.
"""

from __future__ import annotations

import re


_SELECTION_VERBS = [
    "선택",
    "골라",
    "고르",
    "열어",
    "눌러",
    "클릭",
    "들어가",
    "들어가줘",
    "선택해",
    "선택해줘",
    "열어줘",
    "눌러줘",
    "클릭해",
    "클릭해줘",
]


def is_selection_request(text: str) -> bool:
    if not text:
        return False
    if any(verb in text for verb in _SELECTION_VERBS):
        return True
    # Allow explicit ordinal with product keyword and verb-like suffix.
    if re.search(r"(첫|두|세|네|\\d+)\\s*번째\\s*상품", text):
        return any(verb in text for verb in ("선택", "열어", "눌러", "클릭", "골라", "고르"))
    return False


def is_ranking_query(text: str) -> bool:
    if not text:
        return False
    if re.search(r"\\d+\\s*(?:번째|번)", text):
        return False
    keywords = [
        "가장", "제일", "최고", "최대", "최저",
        "높은", "낮은", "많은", "적은", "싼", "저렴", "비싼",
    ]
    return any(k in text for k in keywords)
