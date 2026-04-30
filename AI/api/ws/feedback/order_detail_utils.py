# -*- coding: utf-8 -*-
"""
Utility helpers for order detail handling.
"""

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from api.order.order_client import OrderItem
from .product_detail_utils import normalize_category_path
from .order_detail_constants import ACTION_LABELS


def resolve_page_url(session_manager, session_id: str, data: Dict[str, Any]) -> str:
    page_data = data.get("page_data") if isinstance(data, dict) else None
    url = page_data.get("url") if isinstance(page_data, dict) else None
    result = data.get("result") if isinstance(data, dict) else None
    if not url and isinstance(result, dict):
        url = result.get("current_url") or result.get("page_url") or result.get("url")
    if not url and session_manager:
        session = session_manager.get_session(session_id)
        if session:
            url = session.current_url
    return url or ""


def is_order_detail_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        return "mc.coupang.com" in host and bool(re.search(r"/ssr/desktop/order/\d+", path))
    except Exception:
        return False


def extract_order_id_from_order_detail_url(url: str) -> str:
    if not url:
        return ""
    try:
        match = re.search(r"/ssr/desktop/order/(\d+)", url)
        return match.group(1) if match else ""
    except Exception:
        return ""


def is_order_detail_question(text: str) -> bool:
    if not text:
        return False
    if is_order_cancel_intent(text):
        return False
    keywords = [
        "주문",
        "배송",
        "결제",
        "금액",
        "상품",
        "받는",
        "주소",
        "상태",
        "도착",
        "언제",
        "어디",
        "뭐",
        "정보",
        "내역",
        "상세",
        "읽어",
        "알려",
        "보여",
    ]
    return any(word in text for word in keywords)


def is_order_cancel_intent(text: str) -> bool:
    if not text:
        return False
    normalized = "".join(text.split())
    if "주문취소" in normalized or "배송취소" in normalized:
        return True
    if "취소" in normalized and "주문" in normalized:
        return True
    return False


def is_order_detail_read_request(text: str) -> bool:
    if not text:
        return False
    patterns = [
        "주문 상세 읽어",
        "주문 상세 알려",
        "주문 상세 정보",
        "주문 정보",
        "주문 내역",
    ]
    return any(pat in text for pat in patterns)


def build_order_detail_summary(data: Dict[str, Any]) -> str:
    order = data.get("order") or {}
    text = data.get("text") or {}
    items = data.get("items") or []
    payment = data.get("payment") or {}
    payment_detail = data.get("payment_detail") or {}

    title = order.get("title") or (items[0].get("product_name") if items else "") or ""
    status = text.get("status") or ""
    eta = text.get("eta") or ""
    total = format_won(payment.get("total_payed_amount") or text.get("total_price"))

    parts = ["주문 상세 정보를 안내합니다."]
    if status:
        parts.append(f"현재 상태는 {status}입니다.")
    if eta:
        parts.append(f"도착 예정은 {eta}입니다.")
    if title:
        parts.append(f"상품은 {title}입니다.")
    if total:
        parts.append(f"결제금액은 {total}입니다.")
    return " ".join(parts)


def build_order_detail_payment_tts(data: Dict[str, Any]) -> str:
    payment = data.get("payment") or {}
    payment_detail = data.get("payment_detail") or {}
    text = data.get("text") or {}

    total = format_won(
        payment.get("total_payed_amount")
        or payment_detail.get("total_payed_amount")
        or text.get("total_price")
    )
    product_total = format_won(
        payment.get("total_product_price")
        or payment_detail.get("total_product_price")
    )
    shipping_fee = format_won(
        payment.get("shipping_fee")
        or payment_detail.get("shipping_fee")
    )
    discount = format_won(
        payment.get("discount_amount")
        or payment_detail.get("discount_amount")
    )
    method = (
        payment.get("main_pay_type")
        or payment.get("pay_type")
        or payment_detail.get("pay_method")
        or payment_detail.get("method")
        or ""
    )
    bank = payment.get("bank_name") or payment_detail.get("bank_name") or ""

    parts = []
    if method and bank:
        parts.append(f"결제 수단은 {method} {bank}입니다.")
    elif method:
        parts.append(f"결제 수단은 {method}입니다.")
    elif bank:
        parts.append(f"결제 수단은 {bank}입니다.")

    breakdown_parts = []
    if product_total:
        breakdown_parts.append(f"상품 금액 {product_total}")
    if shipping_fee:
        breakdown_parts.append(f"배송비 {shipping_fee}")
    if discount:
        breakdown_parts.append(f"할인 {discount}")
    if breakdown_parts:
        parts.append(" ".join(breakdown_parts) + "입니다.")

    if total and (method or breakdown_parts):
        parts.append(f"총 결제 금액은 {total}입니다.")

    return " ".join(parts)


def build_order_detail_actions(data: Dict[str, Any]) -> str:
    actions = data.get("actions") or list(ACTION_LABELS)
    action_text = ", ".join(actions)
    return f"가능한 작업은 {action_text} 입니다."


def format_won(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, str):
            cleaned = re.sub(r"[^\d]", "", value)
            if not cleaned:
                return ""
            value = int(cleaned)
        return f"{int(value):,}원"
    except Exception:
        return ""


def truncate_text(text: str, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "..."


def prune_data(obj: Any, depth: int = 0, max_depth: int = 4) -> Any:
    if depth >= max_depth:
        if isinstance(obj, dict):
            return {"_summary": f"{len(obj)} keys"}
        if isinstance(obj, list):
            return {"_summary": f"{len(obj)} items"}
        return obj
    if isinstance(obj, dict):
        pruned: Dict[str, Any] = {}
        for idx, (key, value) in enumerate(obj.items()):
            if idx >= 30:
                pruned["_truncated"] = True
                break
            pruned[key] = prune_data(value, depth + 1, max_depth)
        return pruned
    if isinstance(obj, list):
        return [prune_data(item, depth + 1, max_depth) for item in obj[:10]]
    if isinstance(obj, str):
        return obj if len(obj) <= 200 else obj[:200] + "..."
    return obj


def coerce_int(value: Any, default: int = 1) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        cleaned = re.sub(r"[^\d]", "", str(value))
        if not cleaned:
            return default
        return int(cleaned)
    except Exception:
        return default


def coerce_price(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        cleaned = re.sub(r"[^\d]", "", str(value))
        if not cleaned:
            return None
        return int(cleaned)
    except Exception:
        return None


def build_order_items(order_data: Dict[str, Any]):
    items = []
    raw_items = order_data.get("items") if isinstance(order_data, dict) else None
    if not isinstance(raw_items, list):
        return items
    import logging
    _logger = logging.getLogger(__name__)
    for raw in raw_items:
        if not isinstance(raw, dict):
            _logger.debug("Skipping non-dict item: %s", raw)
            continue
        name = raw.get("product_name") or raw.get("vendor_item_name") or raw.get("name") or ""
        name = str(name).strip()
        if not name:
            _logger.debug("Skipping item with no name: keys=%s", list(raw.keys()))
            continue
        price = coerce_price(raw.get("discounted_unit_price"))
        if price is None:
            price = coerce_price(raw.get("unit_price"))
        if price is None:
            _logger.debug("Skipping item with no price: name=%s keys=%s", name[:30], list(raw.keys()))
            continue
        quantity = coerce_int(raw.get("quantity"), default=1)
        url = raw.get("product_url") or raw.get("url") or ""
        img_url = raw.get("img_url") or raw.get("image") or ""
        deliver_url = raw.get("deliver_url") or raw.get("tracking_url") or ""
        coupang_product_number = (
            raw.get("coupang_product_number")
            or raw.get("coupangProductNumber")
            or raw.get("coupang_product_no")
            or raw.get("coupangProductNo")
            or ""
        )
        category_path = normalize_category_path(
            raw.get("category_path") or raw.get("categoryPath")
        )
        items.append(
            OrderItem(
                name=name,
                price=price,
                quantity=quantity,
                url=url or None,
                img_url=img_url or None,
                deliver_url=deliver_url or None,
                coupang_product_number=coupang_product_number or None,
                category_path=category_path or None,
            )
        )
    if not items and raw_items:
        _logger.warning("No valid items from %d raw items. First item keys: %s", len(raw_items), list(raw_items[0].keys()) if raw_items else [])
    return items


def get_access_token(session_manager, session_id: str) -> str:
    token_keys = [
        "access_token",
        "jwt_token",
        "api_access_token",
        "Authorization",
        "authorization",
        "auth_token",
    ]
    for key in token_keys:
        value = session_manager.get_context(session_id, key)
        if isinstance(value, str) and value.strip():
            token = value.strip()
            if token.lower().startswith("bearer "):
                token = token[7:].strip()
            return token
    return ""


def get_refresh_token(session_manager, session_id: str) -> str:
    token_keys = [
        "refresh_token",
        "refreshToken",
    ]
    for key in token_keys:
        value = session_manager.get_context(session_id, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


__all__ = [
    "resolve_page_url",
    "is_order_detail_url",
    "extract_order_id_from_order_detail_url",
    "is_order_detail_question",
    "is_order_cancel_intent",
    "is_order_detail_read_request",
    "build_order_detail_summary",
    "build_order_detail_actions",
    "build_order_detail_payment_tts",
    "format_won",
    "truncate_text",
    "prune_data",
    "coerce_int",
    "coerce_price",
    "build_order_items",
    "get_access_token",
    "get_refresh_token",
]
