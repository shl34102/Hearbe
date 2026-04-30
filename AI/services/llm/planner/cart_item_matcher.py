from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


_STOPWORDS = {
    "상품", "수량", "변경", "조절", "줄여", "늘려", "올려", "내려",
    "선택", "해제", "취소", "체크", "해주세요", "해줘", "해주세요", "해줘요",
    "그거", "그거요", "그것", "이거", "저거", "요", "좀", "하나", "두개", "두", "세개",
}

_UNITS = {
    "kg", "g", "ml", "l", "개", "팩", "병", "캔", "박스", "세트",
}


@dataclass
class MatchCandidate:
    name: str
    score: float


@dataclass
class MatchResult:
    name: Optional[str]
    score: float
    candidates: List[MatchCandidate]


def match_cart_item_name(
    user_text: str,
    items: List[Dict],
    min_score: float = 0.45,
) -> MatchResult:
    """
    Find the most likely cart item name from user text.

    Returns MatchResult with best name (or None) and scored candidates.
    """
    names = [item.get("name") for item in items if item.get("name")]
    if not names or not user_text:
        return MatchResult(name=None, score=0.0, candidates=[])

    query = _normalize(user_text)
    if not query:
        return MatchResult(name=None, score=0.0, candidates=[])

    query_tokens = _tokens(query)
    candidates: List[MatchCandidate] = []

    for name in names:
        norm_name = _normalize(name)
        score = _score(query, query_tokens, norm_name)
        candidates.append(MatchCandidate(name=name, score=score))

    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0] if candidates else None
    if best and best.score >= min_score:
        return MatchResult(name=best.name, score=best.score, candidates=candidates[:5])

    return MatchResult(name=None, score=best.score if best else 0.0, candidates=candidates[:5])


def prefer_single_selected(items: List[Dict]) -> Optional[str]:
    selected = [item.get("name") for item in items if item.get("selected") is True and item.get("name")]
    if len(selected) == 1:
        return selected[0]
    return None


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\d+[%원]", " ", text)
    text = re.sub(r"\d+(?:[.,]\d+)?", " ", text)
    for unit in _UNITS:
        text = text.replace(unit, " ")
    text = re.sub(r"[^\w가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> List[str]:
    raw = [t for t in text.split() if t and t not in _STOPWORDS]
    return raw


def _score(query: str, query_tokens: List[str], name: str) -> float:
    if not name:
        return 0.0
    name_tokens = _tokens(name)
    if not name_tokens:
        return 0.0

    overlap = _jaccard(query_tokens, name_tokens)
    contains_boost = 0.15 if query and query in name else 0.0
    token_boost = 0.0
    if query_tokens:
        hit = sum(1 for t in query_tokens if t in name_tokens)
        token_boost = min(hit / max(len(query_tokens), 1), 1.0) * 0.25

    return min(overlap + contains_boost + token_boost, 1.0)


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0
