# -*- coding: utf-8 -*-
"""Search sort rule (Coupang)."""

import re
from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import build_click_command, build_wait_command
from ..sites.site_manager import get_page_type, get_selector


_SORT_LABELS = [
    ("쿠팡 랭킹순", ("쿠팡랭킹순", "쿠팡 랭킹순", "랭킹순", "랭킹", "인기순", "쿠팡랭킹", "추천순")),
    ("낮은가격순", ("낮은가격순", "낮은 가격순", "가격낮은순", "최저가순", "가격낮은", "저렴한순서", "저렴한순")),
    ("높은가격순", ("높은가격순", "높은 가격순", "가격높은순", "최고가순", "가격높은", "고가순", "고가순서")),
    ("판매량순", ("판매량순", "판매순", "판매량", "많이팔린순", "잘팔리는순")),
    ("최신순", ("최신순", "신상품순", "새상품순")),
    ("리뷰순", ("리뷰순", "별점순", "평점순")),
]


class SearchSortRule(BaseRule):
    """Sort search results on Coupang search page."""

    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not text:
            return None
        if get_page_type(current_url) != "search":
            return None
        if current_site and getattr(current_site, "site_id", "") != "coupang":
            return None

        label = _detect_sort_label(text)
        if not label:
            return None

        wrapper = get_selector(current_url, "sort_wrapper") or "div[class*='srp_sortWrapper']"
        selector = (
            f"{wrapper} label:has-text('{label}'), "
            f"{wrapper} button:has-text('{label}'), "
            f"{wrapper} a:has-text('{label}')"
        )
        commands = [
            build_click_command(selector, f"{label} 정렬"),
            build_wait_command(1200, "정렬 적용 대기"),
        ]

        return RuleResult(
            matched=True,
            commands=commands,
            response_text=f"{label}으로 정렬합니다.",
            rule_name="search_sort",
        )


def _detect_sort_label(text: str) -> Optional[str]:
    normalized = re.sub(r"\s+", "", text)
    for label, patterns in _SORT_LABELS:
        if any(p in normalized for p in patterns):
            return label
    return None


__all__ = ["SearchSortRule"]
