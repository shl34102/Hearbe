# -*- coding: utf-8 -*-
"""
Search cheapest-product action (session-aware).

This is intentionally not an LLM task:
- We already have extracted search results in session.context["search_results"].
- Deterministic parsing avoids slow/fragile LLM fallback.
"""

from __future__ import annotations

import re
from typing import Optional, Any

from core.interfaces import LLMResponse


_WS_RE = re.compile(r"\s+")
_PRICE_RE = re.compile(r"[0-9]+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def _is_cheapest_intent(norm: str) -> bool:
    compact = norm.replace(" ", "")
    keywords = (
        "가장싼",
        "제일싼",
        "최저가",
        "가장저렴",
        "제일저렴",
        "싸게",
        "저렴한",
    )
    return any(k in compact for k in keywords)


def _parse_price_to_int(price: Any) -> Optional[int]:
    if price is None:
        return None
    s = str(price)
    nums = _PRICE_RE.findall(s.replace(",", ""))
    if not nums:
        return None
    try:
        return int("".join(nums))
    except Exception:
        return None


def handle_search_cheapest_action(user_text: str, session) -> Optional[LLMResponse]:
    """
    Returns a read-only response describing the cheapest item among current search results.
    """
    if not session or not getattr(session, "context", None):
        return None

    norm = _normalize(user_text)
    if not norm or not _is_cheapest_intent(norm):
        return None

    results = session.context.get("search_results") or []
    if not isinstance(results, list) or not results:
        return None

    # Prefer items with parsable price; fall back to first item.
    best_item = None
    best_price = None
    for item in results:
        if not isinstance(item, dict):
            continue
        p = _parse_price_to_int(item.get("price"))
        if p is None:
            continue
        if best_price is None or p < best_price:
            best_price = p
            best_item = item

    if best_item is None:
        best_item = next((x for x in results if isinstance(x, dict)), None)
        if not best_item:
            return None

    idx = best_item.get("index")
    name = best_item.get("name") or best_item.get("title") or "상품"
    price = best_item.get("price") or ""

    if idx:
        text = f"가장 싼 상품은 {idx}번 {name}이고, 가격은 {price}입니다. {idx}번 상품을 열어드릴까요?"
    else:
        text = f"가장 싼 상품은 {name}이고, 가격은 {price}입니다. 이 상품을 열어드릴까요?"

    return LLMResponse(text=text, commands=[], requires_flow=False, flow_type=None)


__all__ = ["handle_search_cheapest_action"]

