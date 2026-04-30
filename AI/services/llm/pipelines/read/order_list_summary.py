# -*- coding: utf-8 -*-
"""
Read-only order list summary pipeline.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from core.interfaces import LLMResponse, SessionState
from services.llm.sites.site_manager import get_page_type
from services.llm.pipelines.shared.intent_guard import has_action_intent


READ_KEYWORDS = (
    "주문 목록",
    "주문목록",
    "주문 내역",
    "주문내역",
    "주문 리스트",
    "주문리스트",
    "읽어",
    "들려",
    "보여",
    "확인",
    "조회",
)


def _extract_orders(order_list) -> List[Dict[str, Any]]:
    if isinstance(order_list, list):
        return [item for item in order_list if isinstance(item, dict)]
    if isinstance(order_list, dict):
        raw = order_list.get("orders") or order_list.get("items") or order_list.get("order_list")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    return []


def handle_order_list_summary_read(
    user_text: str,
    session: Optional[SessionState],
    allow_action: bool = False,
) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None
    current_url = session.current_url or ""
    if not current_url or get_page_type(current_url) != "orderlist":
        return None

    text = (user_text or "").strip()
    if not text:
        return None
    if not any(keyword in text for keyword in READ_KEYWORDS):
        return None
    if not allow_action and has_action_intent(text):
        return None

    orders = _extract_orders(session.context.get("order_list"))
    if not orders:
        return None

    from api.ws.order.order_list_reader import build_order_list_read_tts

    tts_text = build_order_list_read_tts(orders)
    return LLMResponse(
        text=tts_text,
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


__all__ = ["handle_order_list_summary_read"]
