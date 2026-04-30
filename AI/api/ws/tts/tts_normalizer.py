# -*- coding: utf-8 -*-
"""
TTS text normalizer.

 - Strip lightweight Markdown markers.
 - Normalize dates, percentages, won, and unit expressions.
 - Convert English words to Korean-friendly pronunciation.
"""

from __future__ import annotations

import re

from .tts_english_korean import convert_english_to_korean


_UNIT_PATTERNS = [
    # liters
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:l|L)(?=x|X|\b|[^A-Za-z])"), r"\1리터"),
    # milliliters
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:ml|mL|Ml|ML)(?=x|X|\b|[^A-Za-z])"), r"\1밀리리터"),
    # kilograms
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:kg|Kg|kG|KG)(?=x|X|\b|[^A-Za-z])"), r"\1킬로그램"),
    # grams (lowercase only to avoid 5G)
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:g)(?=x|X|\b|[^A-Za-z])"), r"\1그램"),
    # milligrams
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:mg|mG|Mg|MG)(?=x|X|\b|[^A-Za-z])"), r"\1밀리그램"),
]


_KOR_DIGITS = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
_SMALL_UNITS = ["", "십", "백", "천"]
_LARGE_UNITS = ["", "만", "억", "조", "경"]


def _int_to_korean(num: int) -> str:
    if num == 0:
        return "영"

    parts = []
    unit_index = 0
    while num > 0:
        chunk = num % 10000
        if chunk:
            chunk_text = _chunk_to_korean(chunk)
            unit = _LARGE_UNITS[unit_index]
            parts.append(chunk_text + unit)
        num //= 10000
        unit_index += 1

    return " ".join(reversed(parts)).strip()


def _chunk_to_korean(chunk: int) -> str:
    result = []
    for i in range(4):
        digit = chunk % 10
        if digit:
            digit_text = _KOR_DIGITS[digit]
            unit = _SMALL_UNITS[i]
            if digit == 1 and unit:
                digit_text = ""
            result.append(digit_text + unit)
        chunk //= 10
    return "".join(reversed(result)).strip()


def _parse_int(value: str) -> int:
    return int(value.replace(",", ""))


def _replace_percent(match: re.Match) -> str:
    value = match.group(1)
    try:
        number = _parse_int(value)
    except ValueError:
        return match.group(0)
    return f"{_int_to_korean(number)}퍼센트"


def _replace_won(match: re.Match) -> str:
    value = match.group(1)
    try:
        number = _parse_int(value)
    except ValueError:
        return match.group(0)
    return f"{_int_to_korean(number)}원"


def _replace_comma_number(match: re.Match) -> str:
    value = match.group(1)
    try:
        number = _parse_int(value)
    except ValueError:
        return match.group(0)
    return _int_to_korean(number)


_PERCENT_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\s*%")
_WON_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\s*원")
_COMMA_NUMBER_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})+)")
_DATE_SLASH_PATTERN = re.compile(r"(?<!\d)(1[0-2]|0?[1-9])\s*/\s*(3[01]|[12]\d|0?[1-9])(?!\d)")
_DATE_CONTEXT_PATTERN = re.compile(
    r"(입금|배송|보장|예정|이전|이후|반품|다음|내일|모레)"
)


def _normalize_date_slash(text: str) -> str:
    def _repl(match: re.Match) -> str:
        start, end = match.span()
        window = text[max(0, start - 10):min(len(text), end + 10)]
        if not _DATE_CONTEXT_PATTERN.search(window):
            return match.group(0)
        month = int(match.group(1))
        day = int(match.group(2))
        return f"{month}월 {day}일"

    return _DATE_SLASH_PATTERN.sub(_repl, text)


_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_CODE = re.compile(r"`([^`]+)`")
_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC = re.compile(r"\*([^*]+)\*")
_MD_UNDERLINE = re.compile(r"__([^_]+)__")
_MD_UNDER = re.compile(r"_([^_]+)_")
_MD_STRIKE = re.compile(r"~~([^~]+)~~")


def _strip_markdown(text: str) -> str:
    if not text:
        return text
    stripped = _MD_LINK.sub(r"\1", text)
    stripped = _MD_CODE.sub(r"\1", stripped)
    stripped = _MD_BOLD.sub(r"\1", stripped)
    stripped = _MD_ITALIC.sub(r"\1", stripped)
    stripped = _MD_UNDERLINE.sub(r"\1", stripped)
    stripped = _MD_UNDER.sub(r"\1", stripped)
    stripped = _MD_STRIKE.sub(r"\1", stripped)
    stripped = re.sub(r"(?m)^\s*#+\s+", "", stripped)
    stripped = re.sub(r"(?m)^\s*>\s+", "", stripped)
    stripped = re.sub(r"(?m)^\s*[-*]\s+", "", stripped)
    return stripped


def normalize_tts_text(text: str) -> str:
    if not text:
        return text

    normalized = _strip_markdown(text)
    normalized = _normalize_date_slash(normalized)
    normalized = _PERCENT_PATTERN.sub(_replace_percent, normalized)
    normalized = _WON_PATTERN.sub(_replace_won, normalized)
    normalized = _COMMA_NUMBER_PATTERN.sub(_replace_comma_number, normalized)
    for pattern, repl in _UNIT_PATTERNS:
        normalized = pattern.sub(repl, normalized)
    normalized = convert_english_to_korean(normalized)
    return normalized
