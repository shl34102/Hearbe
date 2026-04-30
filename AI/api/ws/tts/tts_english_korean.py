# -*- coding: utf-8 -*-
"""
English -> Korean pronunciation converter (lightweight).

Goal: avoid letter-by-letter TTS for English words by emitting
approximate Hangul syllables (dictionary + fallback transliteration).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple, Optional


_DIRECT_MAP: Dict[str, str] = {
    "lotte": "롯데",
    "coupang": "쿠팡",
    "naver": "네이버",
    "samsung": "삼성",
    "lg": "엘지",
    "hyundai": "현대",
    "kia": "기아",
    "kakao": "카카오",
    "line": "라인",
    "google": "구글",
    "apple": "애플",
    "microsoft": "마이크로소프트",
    "amazon": "아마존",
    "natural": "내추럴",
    "mineral": "미네랄",
    "water": "워터",
    "original": "오리지널",
    "classic": "클래식",
    "premium": "프리미엄",
    "zero": "제로",
    "cola": "콜라",
    "mini": "미니",
    "max": "맥스",
    "pro": "프로",
    "plus": "플러스",
    "ultra": "울트라",
}


_LETTER_MAP: Dict[str, str] = {
    "A": "에이",
    "B": "비",
    "C": "씨",
    "D": "디",
    "E": "이",
    "F": "에프",
    "G": "지",
    "H": "에이치",
    "I": "아이",
    "J": "제이",
    "K": "케이",
    "L": "엘",
    "M": "엠",
    "N": "엔",
    "O": "오",
    "P": "피",
    "Q": "큐",
    "R": "알",
    "S": "에스",
    "T": "티",
    "U": "유",
    "V": "비",
    "W": "더블유",
    "X": "엑스",
    "Y": "와이",
    "Z": "지",
}


_WORD_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z']*)(?![A-Za-z0-9])")


def convert_english_to_korean(text: str) -> str:
    if not text:
        return text

    def _replace(match: re.Match) -> str:
        word = match.group(1)
        if not word:
            return word
        lower = word.lower()
        if lower in _DIRECT_MAP:
            return _DIRECT_MAP[lower]
        if word.isupper() and len(word) <= 4:
            return _spell_letters(word)
        return _transliterate_word(lower)

    return _WORD_PATTERN.sub(_replace, text)


def _spell_letters(word: str) -> str:
    letters = []
    for ch in word:
        mapped = _LETTER_MAP.get(ch.upper())
        if mapped:
            letters.append(mapped)
    return "".join(letters) or word


_CHOSEONG = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ",
    "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ",
    "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]
_JUNGSEONG = [
    "ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ",
    "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ",
    "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ",
    "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ",
    "ㅣ",
]
_JONGSEONG = [
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ",
    "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ",
    "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ",
    "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ",
    "ㅌ", "ㅍ", "ㅎ",
]
_JONG_INDEX = {jamo: idx for idx, jamo in enumerate(_JONGSEONG)}
_CHO_INDEX = {jamo: idx for idx, jamo in enumerate(_CHOSEONG)}
_JUNG_INDEX = {jamo: idx for idx, jamo in enumerate(_JUNGSEONG)}


_VOWEL_MAP: Dict[str, str] = {
    "yeo": "ㅕ",
    "yae": "ㅒ",
    "wae": "ㅙ",
    "ae": "ㅐ",
    "ai": "ㅔ",
    "ay": "ㅔ",
    "ea": "ㅣ",
    "ee": "ㅣ",
    "ie": "ㅣ",
    "ei": "ㅔ",
    "oa": "ㅗ",
    "oo": "ㅜ",
    "ou": "ㅗ",
    "ow": "ㅗ",
    "ui": "ㅢ",
    "eu": "ㅡ",
    "oi": "ㅚ",
    "oy": "ㅚ",
    "ya": "ㅑ",
    "ye": "ㅖ",
    "yo": "ㅛ",
    "yu": "ㅠ",
    "wa": "ㅘ",
    "we": "ㅞ",
    "wi": "ㅟ",
    "wo": "ㅝ",
    "a": "ㅏ",
    "e": "ㅔ",
    "i": "ㅣ",
    "o": "ㅗ",
    "u": "ㅜ",
    "y": "ㅣ",
}


_ONSET_MAP: Dict[str, str] = {
    "b": "ㅂ", "c": "ㅋ", "d": "ㄷ", "f": "ㅍ",
    "g": "ㄱ", "h": "ㅎ", "j": "ㅈ", "k": "ㅋ",
    "l": "ㄹ", "m": "ㅁ", "n": "ㄴ", "p": "ㅍ",
    "q": "ㅋ", "r": "ㄹ", "s": "ㅅ", "t": "ㅌ",
    "v": "ㅂ", "w": "ㅇ", "y": "ㅇ", "z": "ㅈ",
    "ch": "ㅊ", "sh": "ㅅ", "th": "ㅅ", "ph": "ㅍ",
    "wh": "ㅇ", "ng": "ㅇ",
    "kk": "ㄲ", "pp": "ㅃ", "tt": "ㄸ", "ss": "ㅆ", "jj": "ㅉ",
}


_CODA_MAP: Dict[str, str] = {
    "b": "ㅂ", "c": "ㄱ", "d": "ㄷ", "f": "ㅍ",
    "g": "ㄱ", "k": "ㄱ", "l": "ㄹ", "m": "ㅁ",
    "n": "ㄴ", "p": "ㅂ", "r": "ㄹ", "s": "ㅅ",
    "t": "ㅌ", "v": "ㅂ", "z": "ㅅ", "ng": "ㅇ",
    "ch": "ㅊ", "sh": "ㅅ", "th": "ㅌ", "ph": "ㅍ",
}


def _transliterate_word(word: str) -> str:
    word = re.sub(r"[^a-z]", "", word or "")
    if not word:
        return ""
    word = word.replace("x", "ks")
    i = 0
    syllables = []
    while i < len(word):
        if _is_vowel_start(word, i):
            onset = ""
        else:
            onset, olen = _parse_onset(word, i)
            i += olen
        vowel, vlen = _parse_vowel(word, i)
        if not vowel:
            if syllables:
                syllables[-1] = _append_coda(syllables[-1], onset)
            else:
                syllables.append(_spell_letters(onset))
            continue
        i += vlen
        coda, clen = _parse_coda(word, i)
        i += clen
        syllables.append(_compose_syllable(onset, vowel, coda))
    return "".join([s for s in syllables if s])


def _is_vowel_start(word: str, index: int) -> bool:
    return bool(_parse_vowel(word, index)[0])


def _parse_vowel(word: str, index: int) -> Tuple[Optional[str], int]:
    for length in (3, 2, 1):
        seg = word[index:index + length]
        if seg in _VOWEL_MAP:
            return seg, length
    return None, 0


def _parse_onset(word: str, index: int) -> Tuple[str, int]:
    for token in ("sch", "ch", "sh", "th", "ph", "wh", "ng", "kk", "pp", "tt", "ss", "jj"):
        if word.startswith(token, index):
            return token, len(token)
    ch = word[index]
    if ch == "c":
        nxt = word[index + 1:index + 2]
        if nxt in ("e", "i", "y"):
            return "s", 1
    if ch == "g":
        nxt = word[index + 1:index + 2]
        if nxt in ("e", "i", "y"):
            return "j", 1
    return ch, 1


def _parse_coda(word: str, index: int) -> Tuple[str, int]:
    if index >= len(word):
        return "", 0
    if _is_vowel_start(word, index):
        return "", 0
    for token in ("ng", "ck", "sh", "ch", "th", "ph"):
        if word.startswith(token, index):
            nxt = index + len(token)
            if nxt < len(word) and _is_vowel_start(word, nxt):
                return "", 0
            return token, len(token)
    if index + 1 < len(word) and _is_vowel_start(word, index + 1):
        return "", 0
    return word[index], 1


def _compose_syllable(onset: str, vowel: str, coda: str) -> str:
    onset_jamo = _ONSET_MAP.get(onset, "ㅇ")
    vowel_jamo = _VOWEL_MAP.get(vowel, "ㅣ")
    coda_jamo = _CODA_MAP.get(coda, "")
    return _compose(onset_jamo, vowel_jamo, coda_jamo)


def _compose(cho: str, jung: str, jong: str = "") -> str:
    if cho not in _CHO_INDEX or jung not in _JUNG_INDEX:
        return ""
    cho_index = _CHO_INDEX[cho]
    jung_index = _JUNG_INDEX[jung]
    jong_index = _JONG_INDEX.get(jong, 0)
    return chr(0xAC00 + 588 * cho_index + 28 * jung_index + jong_index)


def _append_coda(syllable: str, coda: str) -> str:
    if not syllable:
        return syllable
    code = ord(syllable) - 0xAC00
    if code < 0 or code >= 11172:
        return syllable
    jong_jamo = _CODA_MAP.get(coda, "")
    if not jong_jamo:
        return syllable
    jong_index = _JONG_INDEX.get(jong_jamo, 0)
    if jong_index == 0:
        return syllable
    cho = code // 588
    jung = (code % 588) // 28
    jong = code % 28
    if jong != 0:
        return syllable
    return chr(0xAC00 + 588 * cho + 28 * jung + jong_index)


__all__ = ["convert_english_to_korean"]
