# -*- coding: utf-8 -*-
"""
Read-only current page info pipeline.

Handles requests like:
- "현재 페이지 정보 읽어줘"
- "지금 화면 뭐야?"

Goal: provide a deterministic, page-type-aware response without invoking the command LLM.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any, List

from core.interfaces import LLMResponse, SessionState
from services.llm.sites.site_manager import get_page_type
from services.llm.pipelines.shared.intent_guard import has_action_intent


PAGE_INFO_PATTERNS = (
    r"(현재|지금)\s*(페이지|화면)",
    r"(페이지|화면)\s*(정보|상태)",
    r"(무슨|어느)\s*(페이지|화면)",
    r"여기\s*(어디|뭐)",
)


def is_page_info_request(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    return any(re.search(pattern, value) for pattern in PAGE_INFO_PATTERNS)


def _extract_orders(order_list: Any) -> List[Dict[str, Any]]:
    if isinstance(order_list, list):
        return [item for item in order_list if isinstance(item, dict)]
    if isinstance(order_list, dict):
        raw = order_list.get("orders") or order_list.get("items") or order_list.get("order_list")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    return []


def handle_page_info_read(
    user_text: str,
    session: Optional[SessionState],
    allow_action: bool = False,
) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None

    text = (user_text or "").strip()
    if not text:
        return None
    if not is_page_info_request(text):
        return None
    if not allow_action and has_action_intent(text):
        return None

    current_url = session.current_url or ""
    page_type = get_page_type(current_url) if current_url else None
    ctx = session.context

    # Page-type-aware summaries (best effort).
    if page_type == "cart":
        from api.ws.cart.cart_reader import build_cart_read_tts

        items = ctx.get("cart_items") or []
        summary = ctx.get("cart_summary") or {}
        if isinstance(items, list):
            return LLMResponse(
                text=build_cart_read_tts(items, summary if isinstance(summary, dict) else {}),
                commands=[],
                requires_flow=False,
                flow_type=None,
            )
        return LLMResponse(text="현재 장바구니 페이지입니다.", commands=[], requires_flow=False, flow_type=None)

    if page_type == "search":
        from api.ws.search.search_reader import build_search_read_tts

        results = ctx.get("search_active_results") or ctx.get("search_results") or []
        if isinstance(results, list) and results:
            start_index = ctx.get("search_read_index", 0)
            tts_text, next_index, _ = build_search_read_tts(
                results,
                start_index=start_index,
                count=4,
                include_total=(start_index == 0),
            )
            ctx["search_read_index"] = next_index
            return LLMResponse(text=tts_text, commands=[], requires_flow=False, flow_type=None)
        return LLMResponse(
            text="현재 검색 결과 페이지입니다. 아직 읽을 검색 결과가 없어요.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    if page_type == "orderlist":
        from api.ws.order.order_list_reader import build_order_list_read_tts

        orders = _extract_orders(ctx.get("order_list"))
        if orders:
            return LLMResponse(text=build_order_list_read_tts(orders), commands=[], requires_flow=False, flow_type=None)
        return LLMResponse(
            text="현재 주문 목록 페이지입니다. 아직 주문 목록을 불러오지 못했어요.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    if page_type == "product":
        detail = ctx.get("product_detail")
        if isinstance(detail, dict) and detail:
            name = detail.get("name") or detail.get("title") or detail.get("product_name") or "상품"
            price = detail.get("price") or detail.get("final_price") or detail.get("sale_price") or ""
            if price:
                msg = f"현재 상품 상세 페이지입니다. {name}, 가격은 {price}입니다."
            else:
                msg = f"현재 상품 상세 페이지입니다. {name}입니다."
            return LLMResponse(text=msg, commands=[], requires_flow=False, flow_type=None)
        return LLMResponse(
            text="현재 상품 상세 페이지입니다. 상품 정보를 아직 불러오지 못했어요.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    if page_type == "mall":
        # Hearbe: mall selection page (C/mall, A/mall, B/mall)
        msg = (
            "현재 쇼핑몰 선택 페이지입니다. "
            "1번 쿠팡. 입니다.? "
            "그 외 이동 가능한 페이지는 장바구니, 마이페이지, 로그아웃 입니다."
        )
        return LLMResponse(text=msg, commands=[], requires_flow=False, flow_type=None)

    if page_type:
        return LLMResponse(
            text=f"현재 페이지는 {page_type} 입니다. 어떤 작업을 도와드릴까요?",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )
    return LLMResponse(
        text="현재 페이지를 판단하지 못했어요. 어떤 작업을 도와드릴까요?",
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


__all__ = [
    "handle_page_info_read",
    "is_page_info_request",
]
