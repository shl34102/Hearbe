# -*- coding: utf-8 -*-
"""
Session-aware action handler for Hearbe order history.

Handles:
- The follow-up after we ask: "주문 내역을 읽어드릴까요?"
- Direct "주문 내역 읽어줘" style requests when already on /A|B|C/order-history
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.interfaces import LLMResponse, SessionState
from core.korean_datetime import format_date_for_tts


CTX_HEARBE_ORDER_HISTORY_DATA = "hearbe_order_history_data"
CTX_HEARBE_ORDER_HISTORY_RECOMMENDED = "hearbe_order_history_recommended"
CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING = "hearbe_order_history_prompt_pending"
CTX_HEARBE_ORDER_HISTORY_FETCHING = "hearbe_order_history_fetching"

_WS_RE = re.compile(r"\s+")


PLATFORM_NAMES = {
    1: "쿠팡",
    2: "네이버",
    3: "11번가",
    4: "SSG",
    5: "G마켓",
    6: "컬리",
}


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip()


def _is_on_hearbe_order_history(url: str) -> bool:
    u = (url or "").lower()
    return "i14d108.p.ssafy.io" in u and "/order-history" in u


def _is_affirmative(text: str) -> bool:
    keywords = [
        "네",
        "응",
        "예",
        "그래",
        "그래요",
        "맞아",
        "맞아요",
        "어",
        "읽어",
        "읽어줘",
        "읽어주세요",
        "읽어줄래",
        "보여줘",
        "알려줘",
    ]
    return any(word in text for word in keywords)


def _is_negative(text: str) -> bool:
    keywords = [
        "아니",
        "아니요",
        "괜찮아",
        "괜찮아요",
        "싫어",
        "됐어",
        "필요없어",
        "필요 없어",
    ]
    return any(word in text for word in keywords)


def _is_recommendation_request(text: str) -> bool:
    keywords = [
        "추천",
        "추천 상품",
        "추천목록",
        "추천 목록",
        "자주 산",
        "자주산",
        "자주 구매",
        "자주구매",
        "많이 산",
        "많이 구매",
        "재구매",
        "구매 추천",
    ]
    return any(word in text for word in keywords)


def _format_date(raw: Any) -> str:
    return format_date_for_tts(raw)


def _resolve_platform_name(order: Dict[str, Any]) -> str:
    pid = order.get("platform_id") or order.get("platformId")
    try:
        pid_int = int(pid)
    except Exception:
        pid_int = None
    if pid_int in PLATFORM_NAMES:
        return PLATFORM_NAMES[pid_int]
    for key in ("platform_name", "platformName", "mall_name", "mallName"):
        name = order.get(key)
        if name:
            return str(name)
    if pid_int is not None:
        return f"플랫폼 {pid_int}"
    return "기타 쇼핑몰"


def _build_summary_text(orders: List[Dict[str, Any]]) -> str:
    if not orders:
        return "주문 내역이 없습니다."

    total = len(orders)
    max_read = 4
    lines: List[str] = []
    for idx, order in enumerate(orders[:max_read], start=1):
        ordered_at = _format_date(order.get("ordered_at") or order.get("orderedAt") or "")
        platform = _resolve_platform_name(order)
        items = order.get("items") if isinstance(order.get("items"), list) else []
        first_name = ""
        item_count = 0
        if isinstance(items, list):
            item_count = len([it for it in items if isinstance(it, dict)])
            if item_count > 0:
                first = next((it for it in items if isinstance(it, dict)), {})
                first_name = str(first.get("name") or "").strip()
        label = first_name or "상품"
        if item_count > 1:
            label = f"{label} 외 {item_count - 1}건"

        parts = [f"{idx}번 {label}"]
        if ordered_at:
            parts.append(f"주문일 {ordered_at}")
        if platform:
            parts.append(platform)
        lines.append(", ".join(parts))

    intro = f"주문 내역이 {total}건 있습니다. 최근 주문을 알려드릴게요."
    tts_text = intro + " " + ". ".join(lines) + "."
    if total > max_read:
        remain = total - max_read
        tts_text += f" 나머지 {remain}건도 읽어드릴까요?"
    return tts_text


def _build_recommendation_text(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "추천 상품 정보가 없습니다."

    total = len(items)
    max_read = 5
    lines: List[str] = []
    for idx, item in enumerate(items[:max_read], start=1):
        name = str(item.get("name") or "").strip() or "상품"
        count = item.get("purchaseCount") or item.get("purchase_count")
        match = item.get("categoryMatch") or item.get("category_match")
        suffix = ""
        if match:
            suffix = str(match).strip()
        elif count is not None:
            suffix = f"{count}회 구매"
        if suffix:
            lines.append(f"{idx}번 {name}, {suffix}")
        else:
            lines.append(f"{idx}번 {name}")

    intro = f"자주 산 상품 추천은 {total}개입니다. "
    tts_text = intro + ". ".join(lines) + "."
    if total > max_read:
        remain = total - max_read
        tts_text += f" 나머지 {remain}개도 알려드릴까요?"
    return tts_text


def handle_hearbe_order_history_action(user_text: str, session: Optional[SessionState]) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None
    current_url = session.current_url or ""
    if not _is_on_hearbe_order_history(current_url):
        return None

    text = _normalize(user_text)
    if not text:
        return None

    prompt_pending = bool(session.context.get(CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING))
    orders_raw = session.context.get(CTX_HEARBE_ORDER_HISTORY_DATA)
    recs_raw = session.context.get(CTX_HEARBE_ORDER_HISTORY_RECOMMENDED)
    orders: List[Dict[str, Any]] = []
    recs: List[Dict[str, Any]] = []
    if isinstance(orders_raw, list):
        orders = [o for o in orders_raw if isinstance(o, dict)]
    if isinstance(recs_raw, list):
        recs = [r for r in recs_raw if isinstance(r, dict)]
    if not orders_raw and not recs_raw:
        # If the page handler is still fetching, don't fall back to LLM/extractors.
        if session.context.get(CTX_HEARBE_ORDER_HISTORY_FETCHING):
            return LLMResponse(
                text="?? ??? ???? ????. ??? ??? ???.",
                commands=[],
                requires_flow=False,
                flow_type=None,
            )

    if _is_recommendation_request(text):
        session.context[CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING] = False
        return LLMResponse(
            text=_build_recommendation_text(recs),
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    # If we asked "읽어드릴까요?" then interpret yes/no first.
    if prompt_pending:
        if _is_affirmative(text):
            session.context[CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING] = False
            return LLMResponse(
                text=_build_summary_text(orders),
                commands=[],
                requires_flow=False,
                flow_type=None,
            )
        if _is_negative(text):
            session.context[CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING] = False
            return LLMResponse(
                text="알겠습니다. 원하시는 작업을 말씀해 주세요.",
                commands=[],
                requires_flow=False,
                flow_type=None,
            )

    # Direct read intent while on the page.
    read_keywords = ("읽어", "알려", "보여", "확인", "조회")
    if any(k in text for k in read_keywords):
        session.context[CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING] = False
        return LLMResponse(
            text=_build_summary_text(orders),
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    return None


__all__ = ["handle_hearbe_order_history_action"]
