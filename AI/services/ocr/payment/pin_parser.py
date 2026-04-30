# -*- coding: utf-8 -*-
"""
PIN parser for spoken Korean digits.

Keeps parsing logic isolated from handlers for maintainability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


_KOR_DIGIT_MAP: Dict[str, str] = {
    "\uc601": "0",  # 영
    "\uacf5": "0",  # 공
    "\ube75": "0",  # 빵
    "\uc81c\ub85c": "0",  # 제로
    "\uc77c": "1",  # 일
    "\ud558\ub098": "1",  # 하나
    "\ud55c": "1",  # 한
    "\uc774": "2",  # 이
    "\ub458": "2",  # 둘
    "\uc0bc": "3",  # 삼
    "\uc14b": "3",  # 셋
    "\uc0ac": "4",  # 사
    "\ub137": "4",  # 넷
    "\uc624": "5",  # 오
    "\uc721": "6",  # 육
    "\ub959": "6",  # 륙
    "\uce60": "7",  # 칠
    "\ud314": "8",  # 팔
    "\uad6c": "9",  # 구
}

# Common ASR confusions for keypad digits.
_ASR_MISHEAR: Dict[str, str] = {
    "\ubd80": "9",  # 부 -> 구
    "\uc720": "6",  # 유 -> 육
}

_KEYWORDS = [
    "\ube44\ubc00\ubc88\ud638",  # 비밀번호
    "\ube44\ubc00\ubc88",  # 비밀번
    "\ube44\ubc88",  # 비번
    "\ud540",  # PIN
    "\uc778\uc99d\ubc88\ud638",  # 인증번호
    "\uacb0\uc81c \ube44\ubc00\ubc88\ud638",  # 결제 비밀번호
    "\uce74\ub4dc \ube44\ubc00\ubc88\ud638",  # 카드 비밀번호
]

_TRAILING_SUFFIXES = [
    "\uc774\uc57c",  # 이야
    "\uc774\uc5d0\uc694",  # 이에요
    "\uc608\uc694",  # 예요
    "\uc785\ub2c8\ub2e4",  # 입니다
    "\uc694",  # 요
    "\uc8e0",  # 죠
    "\uc57c",  # 야
]

_LEADING_PARTICLES = [
    "\uc740",  # 은
    "\ub294",  # 는
    "\uc744",  # 을
    "\ub97c",  # 를
    "\ub85c",  # 로
    "\uc73c\ub85c",  # 으로
]


@dataclass(frozen=True)
class PinParseResult:
    digits: List[str]
    used_keyword: bool = False


class PinParser:
    """Rule-based PIN digit parser."""

    def parse(self, text: str) -> PinParseResult:
        if not text:
            return PinParseResult(digits=[])

        digits = re.findall(r"\d", text)
        if digits:
            return PinParseResult(digits=digits)

        used_keyword, remainder = _slice_after_keyword(text)
        cleaned = _normalize_text(remainder)
        if not cleaned:
            return PinParseResult(digits=[], used_keyword=used_keyword)

        cleaned = _strip_leading_particles(cleaned)
        compact = cleaned.replace(" ", "")
        compact = _strip_trailing_suffixes(compact)

        digits = re.findall(r"\d", compact)
        if digits:
            digits = _trim_digits(digits, used_keyword)
            return PinParseResult(digits=digits, used_keyword=used_keyword)

        parsed = _parse_korean_digits(compact)
        parsed = _trim_digits(parsed, used_keyword)
        return PinParseResult(digits=parsed, used_keyword=used_keyword)


def _slice_after_keyword(text: str) -> Tuple[bool, str]:
    for kw in _KEYWORDS:
        idx = text.find(kw)
        if idx >= 0:
            return True, text[idx + len(kw) :]
    return False, text


def _normalize_text(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\uac00-\ud7a3]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_leading_particles(text: str) -> str:
    if not text:
        return text
    tokens = text.split()
    while tokens and tokens[0] in _LEADING_PARTICLES:
        tokens = tokens[1:]
    return " ".join(tokens)


def _strip_trailing_suffixes(text: str) -> str:
    if not text:
        return text
    changed = True
    while changed:
        changed = False
        for suffix in _TRAILING_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)]
                changed = True
                break
    return text


def _parse_korean_digits(text: str) -> List[str]:
    if not text:
        return []
    tokens = sorted(
        list(_KOR_DIGIT_MAP.keys()) + list(_ASR_MISHEAR.keys()),
        key=len,
        reverse=True,
    )
    digits: List[str] = []
    idx = 0
    while idx < len(text):
        matched = False
        for token in tokens:
            if text.startswith(token, idx):
                digit = _KOR_DIGIT_MAP.get(token) or _ASR_MISHEAR.get(token)
                if digit is not None:
                    digits.append(digit)
                idx += len(token)
                matched = True
                break
        if not matched:
            idx += 1
    return digits


def _trim_digits(digits: List[str], used_keyword: bool) -> List[str]:
    if len(digits) <= 6:
        return digits
    # If a keyword was present, keep the first 6 digits (suffix noise).
    if used_keyword:
        return digits[:6]
    return digits
