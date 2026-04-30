# -*- coding: utf-8 -*-
"""
Korean-friendly product term formatting helpers.

These helpers normalize common product terms for natural Korean TTS output.
"""

from __future__ import annotations

import re
from typing import Any, Dict


_KCAL_RE = re.compile(r"(?i)kcal")
_HACCP_RE = re.compile(r"(?i)H\s*\.?\s*A\s*\.?\s*C\s*\.?\s*C\s*\.?\s*P")
_KS_RE = re.compile(r"(?i)K\s*\.?\s*S")
_KC_RE = re.compile(r"(?i)K\s*\.?\s*C")
_ISO_RE = re.compile(r"(?i)I\s*\.?\s*S\s*\.?\s*O")
_KG_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*kg\b")
_G_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*g\b")
_ML_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*ml\b")
_L_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*l\b")
_MM_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*mm\b")
_CM_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*cm\b")
_SQM_RE = re.compile(r"(?i)(\d[\d,]*\.?\d*)\s*(\u33a1|m2|m²|m\^2)(?![A-Za-z0-9])")
_MIXED_PACK_RE = re.compile(
    r"(?i)(\d[\d,]*\.?\d*)\s*(ml|kg|g|l)\s*(?:x|×)\s*(\d+)\b"
)
_QUANTITY_RE = re.compile(r"(?i)\bquantity\b")
_BONUS_1_1_RE = re.compile(r"(?<!\d)1\s*\+\s*1(?!\d)")
_BONUS_2_1_RE = re.compile(r"(?<!\d)2\s*\+\s*1(?!\d)")
_NUMERIC_XL_RE = re.compile(r"(?i)(?<![A-Za-z0-9])(\d+)\s*X\s*L(?![A-Za-z0-9])")
_X_COUNT_RE = re.compile(r"(?i)(?<![A-Za-z0-9])(X{2,5})L(?![A-Za-z0-9])")
_XL_RE = re.compile(r"(?i)(?<![A-Za-z0-9])XL(?![A-Za-z0-9])")


_NUMBER_WORDS: Dict[int, str] = {
    1: "원",
    2: "투",
    3: "쓰리",
    4: "포",
    5: "파이브",
    6: "식스",
    7: "세븐",
    8: "에이트",
    9: "나인",
    10: "텐",
}


_SINO_DIGITS: Dict[int, str] = {
    1: "일",
    2: "이",
    3: "삼",
    4: "사",
    5: "오",
    6: "육",
    7: "칠",
    8: "팔",
    9: "구",
}


_COUNT_WORDS: Dict[int, str] = {
    1: "한개",
    2: "두개",
    3: "세개",
    4: "네개",
    5: "다섯개",
    6: "여섯개",
    7: "일곱개",
    8: "여덟개",
    9: "아홉개",
    10: "열개",
}


def _parse_int(value: str) -> int | None:
    raw = (value or "").replace(",", "").strip()
    if not raw or "." in raw:
        return None
    if not raw.isdigit():
        return None
    return int(raw)


def _sino_korean_number(value: int) -> str:
    if value == 0:
        return "영"
    if value < 0:
        return str(value)

    parts = []
    for unit_value, unit_word in ((10000, "만"), (1000, "천"), (100, "백"), (10, "십")):
        if value >= unit_value:
            digit = value // unit_value
            value %= unit_value
            if digit > 1:
                parts.append(_SINO_DIGITS[digit])
            elif digit == 1 and unit_value == 10000:
                parts.append(_SINO_DIGITS[digit])
            parts.append(unit_word)

    if value > 0:
        parts.append(_SINO_DIGITS.get(value, str(value)))

    return "".join(parts)


def _format_mixed_pack(match: re.Match[str]) -> str:
    qty_raw = match.group(1)
    unit_raw = match.group(2).lower()
    count_raw = match.group(3)

    qty_value = _parse_int(qty_raw)
    qty_spoken = _sino_korean_number(qty_value) if qty_value is not None else qty_raw.replace(",", "")

    unit_map = {
        "ml": "밀리리터",
        "l": "리터",
        "g": "그램",
        "kg": "킬로그램",
    }
    unit_korean = unit_map.get(unit_raw, unit_raw)

    if qty_spoken == "일":
        qty_unit = f"{qty_spoken}{unit_korean}"
    else:
        qty_unit = f"{qty_spoken} {unit_korean}"

    count_value = _parse_int(count_raw)
    count_word = _COUNT_WORDS.get(count_value, f"{count_raw}개")
    return f"{qty_unit} {count_word}"


def format_product_terms_for_tts(value: Any) -> str:
    """
    Replace common product terms with Korean-friendly spoken forms.

    Examples:
      - "120kcal" -> "120칼로리"
      - "XL" -> "엑스라지"
      - "2XL" / "XXL" -> "투 엑스라지"
    """
    if value is None:
        return ""

    text = str(value)
    if not text:
        return text

    text = _QUANTITY_RE.sub("수량", text)
    text = _BONUS_1_1_RE.sub("원 플러스 원", text)
    text = _BONUS_2_1_RE.sub("투 플러스 원", text)
    text = _MIXED_PACK_RE.sub(_format_mixed_pack, text)
    text = _KCAL_RE.sub("칼로리", text)
    text = _HACCP_RE.sub("해썹", text)
    text = _KS_RE.sub("케이에스", text)
    text = _KC_RE.sub("케이씨", text)
    text = _ISO_RE.sub("아이에스오", text)
    text = _ML_RE.sub(r"\g<1>밀리리터", text)
    text = _L_RE.sub(r"\g<1>리터", text)
    text = _KG_RE.sub(r"\g<1>킬로그램", text)
    text = _G_RE.sub(r"\g<1>그램", text)
    text = _MM_RE.sub(r"\g<1>밀리미터", text)
    text = _CM_RE.sub(r"\g<1>센티미터", text)
    text = _SQM_RE.sub(r"\g<1>제곱미터", text)

    def _replace_numeric_xl(match: re.Match[str]) -> str:
        raw = match.group(1)
        try:
            count = int(raw)
        except ValueError:
            return match.group(0)
        word = _NUMBER_WORDS.get(count, str(count))
        return f"{word} 엑스라지"

    text = _NUMERIC_XL_RE.sub(_replace_numeric_xl, text)

    def _replace_x_count(match: re.Match[str]) -> str:
        count = len(match.group(1))
        word = _NUMBER_WORDS.get(count, str(count))
        return f"{word} 엑스라지"

    text = _X_COUNT_RE.sub(_replace_x_count, text)
    text = _XL_RE.sub("엑스라지", text)

    return text


__all__ = ["format_product_terms_for_tts"]
