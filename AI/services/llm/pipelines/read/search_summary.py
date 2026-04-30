# -*- coding: utf-8 -*-
"""
Read-only search summary pipeline.
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import LLMResponse, SessionState
from services.llm.sites.site_manager import get_page_type
from services.llm.pipelines.shared.intent_guard import has_action_intent


READ_KEYWORDS = (
    "검색 결과",
    "검색결과",
    "결과",
    "상품 목록",
    "상품목록",
    "목록",
    "읽어",
    "들려",
    "보여",
    "요약",
    "전체",
)


def handle_search_summary_read(
    user_text: str,
    session: Optional[SessionState],
    allow_action: bool = False,
) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None
    current_url = session.current_url or ""
    if not current_url or get_page_type(current_url) != "search":
        return None

    text = (user_text or "").strip()
    if not text:
        return None
    if not any(keyword in text for keyword in READ_KEYWORDS):
        return None
    if not allow_action and has_action_intent(text):
        return None

    results = session.context.get("search_active_results") or session.context.get("search_results") or []
    if not isinstance(results, list) or not results:
        return None

    start_index = session.context.get("search_read_index", 0)
    from api.ws.search.search_reader import build_search_read_tts

    tts_text, next_index, _ = build_search_read_tts(
        results,
        start_index=start_index,
        count=4,
        include_total=(start_index == 0),
    )
    session.context["search_read_index"] = next_index
    return LLMResponse(
        text=tts_text,
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


__all__ = ["handle_search_summary_read"]
