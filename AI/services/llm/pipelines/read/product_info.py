# -*- coding: utf-8 -*-
"""
Read-only product info pipeline.

Responds to product-info requests using extracted product_detail.
"""

from __future__ import annotations

import re
import time
from typing import Optional, Dict, Any, List

from core.interfaces import LLMResponse, SessionState
from core.korean_product_terms import format_product_terms_for_tts
from services.llm.sites.site_manager import get_page_type
from services.llm.pipelines.shared.intent_guard import has_action_intent


INFO_KEYWORDS = (
    "상품 정보",
    "상품정보",
    "상품 상세",
    "상품상세",
    "상세 정보",
    "상세정보",
    "상품 설명",
    "상품설명",
    "설명",
    "스펙",
    "가격",
)

INFO_PATTERNS = (
    r"\uc0c1\ud488\s*\uc815\ubcf4",
    r"\uc0c1\ud488\s*\uc0c1\uc138",
    r"\uc0c1\uc138\s*\uc815\ubcf4",
    r"\uc0c1\ud488\s*\uc774\ub984",
)


def is_product_info_request(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    if any(keyword in value for keyword in INFO_KEYWORDS):
        return True
    return any(re.search(pattern, value) for pattern in INFO_PATTERNS)


def has_recent_product_detail(session: Optional[SessionState], max_age_sec: float = 120.0) -> bool:
    if not session or not session.context:
        return False
    detail = session.context.get("product_detail")
    if not isinstance(detail, dict) or not detail:
        return False
    ts = session.context.get("product_detail_received_at") or detail.get("_extracted_at")
    if not ts:
        return True
    try:
        age = time.time() - float(ts)
    except (TypeError, ValueError):
        return True
    return age <= max_age_sec


def _format_won(value: str) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    if "원" in text or "₩" in text:
        return text
    if re.search(r"\d", text):
        return f"{text}원"
    return text


def _build_summary(detail: Dict[str, Any]) -> str:
    name = (
        detail.get("name")
        or detail.get("title")
        or detail.get("product_name")
        or ""
    )
    price = detail.get("price") or detail.get("final_price") or detail.get("sale_price") or ""
    discount_rate = detail.get("discount_rate") or ""
    delivery = detail.get("delivery") or detail.get("rocket_delivery") or ""

    parts: List[str] = []
    if name:
        parts.append(f"상품명은 {name}입니다.")
    if price:
        parts.append(f"현재 가격은 {_format_won(str(price))}입니다.")
    if discount_rate:
        parts.append(f"할인율 {discount_rate}입니다.")
    if delivery:
        parts.append(f"배송 정보는 {delivery}입니다.")

    options = detail.get("options") or {}
    if isinstance(options, dict) and options:
        option_text = ", ".join(f"{k} {v}" for k, v in options.items() if v)
        if option_text:
            parts.append(f"선택 옵션은 {option_text}입니다.")

    if not parts:
        return "상품 정보를 찾지 못했어요."

    # OCR 추출 데이터가 있으면 상세 정보 추가
    ocr_summary = detail.get("ocr_summary")
    if isinstance(ocr_summary, list) and ocr_summary:
        ocr_text = " ".join(str(s) for s in ocr_summary if s)
        if ocr_text:
            parts.append(f"상세 정보: {ocr_text}")

    parts = [format_product_terms_for_tts(part) for part in parts]
    return " ".join(parts)


def handle_product_info_read(
    user_text: str,
    session: Optional[SessionState],
    allow_action: bool = False,
) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None
    current_url = session.current_url or ""
    page_type = get_page_type(current_url) if current_url else None

    text = (user_text or "").strip()
    if not text:
        return None
    if not is_product_info_request(text):
        return None
    if not allow_action and has_action_intent(text):
        return None

    detail = session.context.get("product_detail")
    has_detail = isinstance(detail, dict) and bool(detail)
    if page_type != "product" and not has_recent_product_detail(session):
        return None
    if not has_detail:
        return LLMResponse(
            text="상품 정보를 불러오지 못했어요. 다시 시도해 주세요.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    summary = _build_summary(detail)
    return LLMResponse(
        text=summary,
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


__all__ = [
    "handle_product_info_read",
    "has_recent_product_detail",
    "is_product_info_request",
]
