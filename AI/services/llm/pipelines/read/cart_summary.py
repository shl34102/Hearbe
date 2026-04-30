# -*- coding: utf-8 -*-
"""
Read-only cart summary pipeline.
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import LLMResponse, SessionState
from services.llm.sites.site_manager import get_page_type
from services.llm.pipelines.shared.intent_guard import has_action_intent


READ_KEYWORDS = (
    "장바구니",
    "장바구니 내용",
    "장바구니 읽어",
    "장바구니 들려",
    "장바구니 보여",
    "장바구니 확인",
    "장바구니 요약",
    "총액",
    "총 가격",
    "총 상품가격",
    "할인",
    "배송비",
    "최종 가격",
    "결제 금액",
)


def handle_cart_summary_read(
    user_text: str,
    session: Optional[SessionState],
    allow_action: bool = False,
) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None
    current_url = session.current_url or ""
    if not current_url or get_page_type(current_url) != "cart":
        return None

    text = (user_text or "").strip()
    if not text:
        return None
    if not any(keyword in text for keyword in READ_KEYWORDS):
        return None
    if not allow_action and has_action_intent(text):
        return None

    items = session.context.get("cart_items") or []
    summary = session.context.get("cart_summary") or {}
    if not isinstance(items, list):
        return None

    from api.ws.cart.cart_reader import build_cart_read_tts

    tts_text = build_cart_read_tts(items, summary if isinstance(summary, dict) else {})
    return LLMResponse(
        text=tts_text,
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


__all__ = ["handle_cart_summary_read"]
