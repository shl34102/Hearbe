# -*- coding: utf-8 -*-
"""
Order detail rules for Coupang.

Applies only on order detail pages.
"""

import re
from urllib.parse import urlparse
from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import GeneratedCommand
from ..sites.site_manager import get_selector, get_page_type, get_current_site


class OrderDetailRule(BaseRule):
    """주문 상세 페이지 전용 룰"""

    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not text:
            return None
        if not _is_coupang_site(current_url, current_site):
            return None

        page_type = get_page_type(current_url) if current_url else None
        on_order_detail = page_type == "orderdetail" or _looks_like_order_detail_url(current_url or "")
        on_cancel_page = page_type == "ordercancel" or _looks_like_cancel_page_url(current_url or "")
        if not (on_order_detail or on_cancel_page):
            return None

        normalized = _normalize(text)

        # 배송 조회
        if _contains_any(normalized, ["배송조회", "배송확인", "배송조회해"]):
            selector = get_selector(current_url, "track_delivery") if current_url else None
            commands = _build_click(selector, "배송 조회")
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="배송 조회를 진행합니다.",
                rule_name="orderdetail_track_delivery",
            )

        # 장바구니 담기
        if _contains_any(normalized, ["장바구니담기", "장바구니추가", "장바구니넣"]) or "장바구니" in normalized:
            selector = get_selector(current_url, "add_to_cart") if current_url else None
            commands = _build_click(selector, "장바구니 담기")
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="장바구니에 담겠습니다.",
                rule_name="orderdetail_add_to_cart",
            )

        # 주문/배송 취소
        if _contains_any(normalized, ["주문배송취소", "주문취소", "배송취소", "주문취소해", "취소"]):
            if on_cancel_page:
                next_selector = get_selector(current_url, "cancel_next") if current_url else None
                submit_selector = get_selector(current_url, "cancel_submit") if current_url else None
                confirm_selector = get_selector(current_url, "cancel_confirm") if current_url else None
                commands = _build_cancel_flow_on_cancel_page(next_selector, submit_selector, confirm_selector)
            else:
                entry_selector = get_selector(current_url, "cancel_entry") if current_url else None
                if not entry_selector:
                    entry_selector = get_selector(current_url, "cancel_order") if current_url else None
                commands = _build_cancel_entry_flow(entry_selector, None, None, None)
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="주문 취소를 진행합니다.",
                rule_name="orderdetail_cancel",
            )

        # 주문목록 돌아가기
        if _contains_any(normalized, ["주문목록돌아가기", "주문목록", "목록돌아가기", "주문목록가기"]):
            selector = get_selector(current_url, "back_to_orderlist") if current_url else None
            commands = _build_click(selector, "주문목록 돌아가기")
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="주문목록으로 돌아갑니다.",
                rule_name="orderdetail_back_to_list",
            )

        return None


def _normalize(text: str) -> str:
    return "".join(text.split())


def _contains_any(text: str, keys: list[str]) -> bool:
    return any(k in text for k in keys)


def _build_click(selector: Optional[str], fallback_text: str) -> list[GeneratedCommand]:
    if selector:
        return [
            GeneratedCommand(
                tool_name="click",
                arguments={"selector": selector},
                description=f"{fallback_text} 버튼 클릭",
            )
        ]
    return [
        GeneratedCommand(
            tool_name="click_text",
            arguments={"text": fallback_text},
            description=f"{fallback_text} 텍스트 클릭",
        )
    ]


def _build_cancel_entry_flow(
    entry_selector: Optional[str],
    next_selector: Optional[str],
    submit_selector: Optional[str],
    confirm_selector: Optional[str],
) -> list[GeneratedCommand]:
    commands: list[GeneratedCommand] = []
    if entry_selector:
        commands.append(
            GeneratedCommand(
                tool_name="click",
                arguments={"selector": entry_selector},
                description="주문 취소 진입 버튼 클릭",
            )
        )
    else:
        commands.append(
            GeneratedCommand(
                tool_name="click_text",
                arguments={"text": "주문 · 배송 취소"},
                description="주문 · 배송 취소 텍스트 클릭",
            )
        )

    commands.append(
        GeneratedCommand(
            tool_name="wait",
            arguments={"seconds": 1},
            description="주문 취소 페이지 전환 대기",
        )
    )
    commands.extend(_build_cancel_flow_on_cancel_page(next_selector, submit_selector, confirm_selector))
    return commands


def _build_cancel_flow_on_cancel_page(
    next_selector: Optional[str],
    submit_selector: Optional[str],
    confirm_selector: Optional[str],
) -> list[GeneratedCommand]:
    commands: list[GeneratedCommand] = []
    if next_selector:
        commands.append(
            GeneratedCommand(
                tool_name="click",
                arguments={"selector": next_selector},
                description="취소 플로우 다음 단계 클릭",
            )
        )
    else:
        commands.append(
            GeneratedCommand(
                tool_name="click_text",
                arguments={"text": "다음 단계"},
                description="취소 플로우 다음 단계 클릭",
            )
        )

    if submit_selector:
        commands.append(
            GeneratedCommand(
                tool_name="click",
                arguments={"selector": submit_selector},
                description="취소 플로우 신청하기 클릭",
            )
        )
    else:
        commands.append(
            GeneratedCommand(
                tool_name="click_text",
                arguments={"text": "신청하기"},
                description="취소 플로우 신청하기 클릭",
            )
        )
    commands.extend(_build_cancel_confirm_steps(confirm_selector))
    return commands


def _build_cancel_confirm_steps(confirm_selector: Optional[str]) -> list[GeneratedCommand]:
    selector = confirm_selector or "button:has-text('취소 확인'), button:has-text('확인')"
    return [
        GeneratedCommand(
            tool_name="wait_for_selector",
            arguments={"selector": selector, "state": "visible", "timeout": 8000},
            description="취소 확인 모달 대기",
        ),
        GeneratedCommand(
            tool_name="click",
            arguments={"selector": selector},
            description="취소 확인 클릭",
        ),
    ]


def _is_coupang_site(current_url: str, current_site) -> bool:
    if current_site and getattr(current_site, "site_id", "") == "coupang":
        return True
    if current_url and _is_coupang_url(current_url):
        return True
    site = get_current_site(current_url) if current_url else None
    return bool(site and getattr(site, "site_id", "") == "coupang")


def _looks_like_order_detail_url(url: str) -> bool:
    if not url:
        return False
    return bool(re.search(r"mc\\.coupang\\.com/ssr/desktop/order/\\d+", url))


def _looks_like_cancel_page_url(url: str) -> bool:
    if not url:
        return False
    return bool(re.search(r"mc\\.coupang\\.com/ssr/desktop/cancel-flow", url))


def _is_coupang_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return "coupang.com" in host


__all__ = ["OrderDetailRule"]
