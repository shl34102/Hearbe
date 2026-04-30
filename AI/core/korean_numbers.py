"""
Korean number parsing helpers.
"""

from __future__ import annotations

import re
from typing import Optional, Sequence


_SINO_DIGITS = {
    "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5,
    "육": 6, "칠": 7, "팔": 8, "구": 9,
}

_SINO_UNITS = {
    "십": 10,
    "백": 100,
    "천": 1000,
    "만": 10000,
}

_NATIVE_TENS = {
    "열": 10,
    "스무": 20,
    "스물": 20,
    "서른": 30,
    "마흔": 40,
    "쉰": 50,
    "예순": 60,
    "일흔": 70,
    "여든": 80,
    "아흔": 90,
}

_NATIVE_ONES = {
    "한": 1, "하나": 1,
    "두": 2, "둘": 2,
    "세": 3, "셋": 3,
    "네": 4, "넷": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
}

_ORDINAL_NATIVE = {
    "첫": 1,
}

DEFAULT_COUNT_UNITS: Sequence[str] = (
    "개입",
    "매입",
    "세트",
    "박스",
    "팩",
    "개",
    "매",
    "병",
    "캔",
    "장",
    "봉",
    "포",
    "종",
    "입",
)


def parse_korean_number(token: str) -> Optional[int]:
    """
    Parse a Korean or numeric token into an integer.
    Returns None when parsing fails.
    """
    if token is None:
        return None
    token = str(token).strip()
    if not token:
        return None
    if token.isdigit():
        return int(token)
    return _parse_number_token(token)


def replace_korean_number_units(
    text: str,
    units: Optional[Sequence[str]] = None,
) -> str:
    """
    Replace Korean number + unit combinations with digit+unit (e.g., "열두 개" -> "12개").
    """
    if not text:
        return text
    unit_list = list(units) if units else list(DEFAULT_COUNT_UNITS)
    unit_list.sort(key=len, reverse=True)
    pattern = re.compile(rf"([가-힣]+)\s*({'|'.join(map(re.escape, unit_list))})")

    def repl(match: re.Match[str]) -> str:
        value = parse_korean_number(match.group(1))
        if value is None:
            return match.group(0)
        return f"{value}{match.group(2)}"

    return pattern.sub(repl, text)


def extract_ordinal_index(text: str) -> Optional[int]:
    """
    Extract zero-based ordinal index from Korean or numeric ordinals.

    Examples:
      - "30번째" -> 29
      - "서른번째" -> 29
      - "인덱스 삼십번" -> 29
    """
    if not text:
        return None

    match = re.search(r"(\d+)\s*(?:번째|번)", text)
    if match:
        idx = int(match.group(1)) - 1
        return idx if idx >= 0 else None

    # Prefer explicit ordinal markers
    ordinal_match = re.search(r"([가-힣]+)\s*(?:번째|번)", text)
    if ordinal_match:
        token = ordinal_match.group(1)
        value = _parse_number_token(token)
        if value is not None and value > 0:
            return value - 1

    # Fallback: scan Korean tokens in text
    for token in re.findall(r"[가-힣]+", text):
        value = _parse_number_token(token)
        if value is not None and value > 0:
            return value - 1

    return None


def _parse_number_token(token: str) -> Optional[int]:
    token = token.replace(" ", "")
    if not token:
        return None

    if token in _ORDINAL_NATIVE:
        return _ORDINAL_NATIVE[token]

    if token.endswith("째") and len(token) > 1:
        base = token[:-1]
        if base in _ORDINAL_NATIVE:
            return _ORDINAL_NATIVE[base]
        value = _parse_native_korean(base)
        if value is not None:
            return value
        value = _parse_sino_korean(base)
        if value is not None:
            return value

    value = _parse_native_korean(token)
    if value is not None:
        return value

    value = _parse_sino_korean(token)
    if value is not None:
        return value

    # Try suffixes for cases like "인덱스삼십"
    for i in range(1, len(token)):
        suffix = token[i:]
        value = _parse_native_korean(suffix)
        if value is not None:
            return value
        value = _parse_sino_korean(suffix)
        if value is not None:
            return value

    return None


def _parse_native_korean(token: str) -> Optional[int]:
    if not token:
        return None

    if token in _NATIVE_ONES:
        return _NATIVE_ONES[token]
    if token in _NATIVE_TENS:
        return _NATIVE_TENS[token]

    if token.startswith("열"):
        if token == "열":
            return 10
        rest = token[1:]
        if rest in _NATIVE_ONES:
            return 10 + _NATIVE_ONES[rest]

    for tens_word, tens_val in _NATIVE_TENS.items():
        if token.startswith(tens_word):
            rest = token[len(tens_word):]
            if not rest:
                return tens_val
            if rest in _NATIVE_ONES:
                return tens_val + _NATIVE_ONES[rest]

    return None


def _parse_sino_korean(token: str) -> Optional[int]:
    if not token:
        return None

    total = 0
    current = 0
    used = False

    for ch in token:
        if ch in _SINO_DIGITS:
            current = _SINO_DIGITS[ch]
            used = True
        elif ch in _SINO_UNITS:
            used = True
            unit = _SINO_UNITS[ch]
            if unit == 10000:
                base = total + current
                if base == 0:
                    base = 1
                total = base * unit
                current = 0
            else:
                if current == 0:
                    current = 1
                total += current * unit
                current = 0
        else:
            return None

    if not used:
        return None

    total += current
    return total if total > 0 else None
