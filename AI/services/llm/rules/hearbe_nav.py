# -*- coding: utf-8 -*-
"""
Hearbe navigation rules.

Goal: Avoid rule_miss -> LLM fallback for common Hearbe navigation intents
(member info / order history / wishlist / mall / home).
"""

from __future__ import annotations

import re
from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import (
    GeneratedCommand,
    build_goto_command,
    build_wait_command,
    resolve_hearbe_typed_url,
)
from ..sites.site_manager import get_current_site


_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def _is_hearbe_site(current_url: str, current_site) -> bool:
    if current_site and getattr(current_site, "site_id", "") == "hearbe":
        return True
    site = get_current_site(current_url) if current_url else None
    return bool(site and getattr(site, "site_id", "") == "hearbe")


def _is_on_path(current_url: str, suffix: str) -> bool:
    url = (current_url or "").lower()
    return suffix.lower() in url


MY_PAGE_TRIGGERS = (
    "마이페이지",
    "마이 페이지",
    "회원정보",
    "회원 정보",
    "내 정보",
    "내정보",
)

ORDER_HISTORY_TRIGGERS = (
    "주문 내역",
    "주문내역",
    "주문 목록",
    "주문목록",
    "주문 조회",
    "주문조회",
    "주문 리스트",
    "주문리스트",
)

CART_TRIGGERS = (
    "장바구니",
    "카트",
)

WISHLIST_TRIGGERS = (
    "찜한",
    "찜",
    "위시",
    "위시리스트",
)

MALL_TRIGGERS = (
    "쇼핑몰",
    "몰로",
    "몰로 이동",
)

HOME_TRIGGERS = (
    "홈으로",
    "홈",
    "메인으로",
    "메인",
)


class HearbeNavRule(BaseRule):
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not _is_hearbe_site(current_url, current_site):
            return None

        norm = _normalize(text)
        if not norm:
            return None

        commands: list[GeneratedCommand] = []

        # Cart
        if any(kw in norm for kw in CART_TRIGGERS):
            if _is_on_path(current_url, "/cart"):
                return None
            target_url = resolve_hearbe_typed_url(current_site, "/cart", current_url=current_url)
            if target_url:
                commands = [
                    build_goto_command(target_url, "장바구니 페이지로 이동"),
                    build_wait_command(1200, "페이지 로딩 대기"),
                ]
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text="장바구니 페이지로 이동합니다.",
                    rule_name="hearbe_cart",
                )
            return None

        # Order history
        if any(kw in norm for kw in ORDER_HISTORY_TRIGGERS):
            if _is_on_path(current_url, "/order-history"):
                return None
            target_url = resolve_hearbe_typed_url(current_site, "/order-history", current_url=current_url)
            if target_url:
                commands = [
                    build_goto_command(target_url, "주문 내역 페이지로 이동"),
                    build_wait_command(1200, "페이지 로딩 대기"),
                ]
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text="주문 내역 페이지로 이동합니다.",
                    rule_name="hearbe_order_history",
                )
            return None

        # Member info / My page
        if any(kw in norm for kw in MY_PAGE_TRIGGERS):
            if _is_on_path(current_url, "/member-info"):
                return None
            target_url = resolve_hearbe_typed_url(current_site, "/member-info", current_url=current_url)
            if target_url:
                commands = [
                    build_goto_command(target_url, "회원 정보 페이지로 이동"),
                    build_wait_command(1200, "페이지 로딩 대기"),
                ]
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text="마이페이지로 이동합니다.",
                    rule_name="hearbe_member_info",
                )
            return None

        # Wishlist
        if any(kw in norm for kw in WISHLIST_TRIGGERS):
            if _is_on_path(current_url, "/wishlist"):
                return None
            target_url = resolve_hearbe_typed_url(current_site, "/wishlist", current_url=current_url)
            if target_url:
                commands = [
                    build_goto_command(target_url, "찜한 상품 페이지로 이동"),
                    build_wait_command(1200, "페이지 로딩 대기"),
                ]
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text="찜한 상품 페이지로 이동합니다.",
                    rule_name="hearbe_wishlist",
                )
            return None

        # Mall
        if any(kw in norm for kw in MALL_TRIGGERS):
            if _is_on_path(current_url, "/mall"):
                return None
            target_url = resolve_hearbe_typed_url(current_site, "/mall", current_url=current_url)
            if target_url:
                commands = [
                    build_goto_command(target_url, "쇼핑몰 페이지로 이동"),
                    build_wait_command(1200, "페이지 로딩 대기"),
                ]
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text="쇼핑몰 페이지로 이동합니다.",
                    rule_name="hearbe_mall",
                )
            return None

        # Home (main)
        if any(kw == norm or kw in norm for kw in HOME_TRIGGERS):
            if _is_on_path(current_url, "/main"):
                return None
            home_url = current_site.get_url("home") if current_site else None
            if home_url:
                commands = [
                    build_goto_command(home_url, "홈으로 이동"),
                    build_wait_command(1200, "페이지 로딩 대기"),
                ]
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text="홈으로 이동합니다.",
                    rule_name="hearbe_home",
                )
            return None

        return None


__all__ = ["HearbeNavRule"]
