# -*- coding: utf-8 -*-
"""
Hearbe mall selection rule.

Why this exists:
- On Hearbe `/A|/C/mall`, we want to avoid `rule_miss -> LLM fallback` for the
  common intent: "쿠팡으로 이동(해줘)".

Design choice:
- Clicking a mall-card is not deterministic (DOM overlays / JS routing can swallow clicks).
- We navigate directly to Coupang home via `goto` for reliability.
"""

from __future__ import annotations

import re
from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import GeneratedCommand, build_goto_command, build_wait_command
from ..sites.site_manager import get_current_site, get_page_type

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def _is_hearbe_site(current_url: str, current_site) -> bool:
    if current_site and getattr(current_site, "site_id", "") == "hearbe":
        return True
    site = get_current_site(current_url) if current_url else None
    return bool(site and getattr(site, "site_id", "") == "hearbe")


def _is_mall_page(current_url: str) -> bool:
    try:
        return get_page_type(current_url) == "mall"
    except Exception:
        return False


def _wants_coupang(norm: str) -> bool:
    lowered = norm.lower()
    compact = lowered.replace(" ", "")

    # Explicit keyword.
    if "쿠팡" in norm or "coupang" in compact:
        return True

    # Ordinal selection on the mall list.
    # Today only Coupang is exposed, so "1번" can be interpreted as Coupang.
    if compact in ("1번", "일번", "첫번째", "첫번째로", "첫번째로가", "첫번째선택"):
        return True
    if "1번" in compact and any(k in compact for k in ("선택", "이동", "가", "열")):
        return True

    return False


class HearbeMallSelectRule(BaseRule):
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not _is_hearbe_site(current_url, current_site):
            return None
        if not _is_mall_page(current_url):
            return None

        norm = _normalize(text)
        if not norm or not _wants_coupang(norm):
            return None

        coupang_home = "https://www.coupang.com/"
        commands: list[GeneratedCommand] = [
            build_goto_command(coupang_home, "쿠팡으로 이동"),
            build_wait_command(1200, "페이지 로딩 대기"),
        ]
        return RuleResult(
            matched=True,
            commands=commands,
            response_text="쿠팡으로 이동할게요.",
            rule_name="hearbe_mall_select_coupang",
        )


__all__ = ["HearbeMallSelectRule"]

