# -*- coding: utf-8 -*-
"""
Payment post-processor.

Detects Coupang thank-you page and extracts order summary for TTS.
Handles follow-up actions (order detail / continue shopping).
"""

import html as html_lib
import json
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from core.interfaces import MCPCommand

logger = logging.getLogger(__name__)

CTX_THANK_YOU_SNAPSHOT_REQUESTED = "thank_you_snapshot_requested"
CTX_THANK_YOU_ORDER_ID = "thank_you_order_id"
CTX_THANK_YOU_CHECKOUT_ID = "thank_you_checkout_id"

CTX_PAYMENT_POST_WAITING_ACTION = "payment_post_waiting_action"
CTX_PAYMENT_POST_PENDING_ACTION = "payment_post_pending_action"

PENDING_ACTION_MAIN = "main"
PENDING_ACTION_ORDER_DETAIL = "order_detail"

SELECTOR_ORDER_DETAIL_BUTTON = "button:has-text('주문 상세보기')"
SELECTOR_CONTINUE_SHOPPING_BUTTON = "button:has-text('쇼핑 계속하기')"

FOLLOW_UP_TTS = "주문 상세보기로 이동할까요, 아니면 쇼핑을 계속할까요?"
MAIN_PAGE_TTS = "메인페이지"


class PaymentPostHandler:
    """Post-payment handler for thank-you pages and follow-up choices."""

    def __init__(self, sender, session_manager):
        self._sender = sender
        self._session = session_manager

    async def handle_page_update(self, session_id: str, current_url: str) -> bool:
        if not self._sender or not self._session:
            return False
        handled = await self._handle_pending_action(session_id, current_url)
        if not _is_thank_you_url(current_url):
            return handled

        info = _extract_thank_you_from_url(current_url)
        if _is_duplicate_order(self._session, session_id, info):
            return True

        already = self._session.get_context(session_id, CTX_THANK_YOU_SNAPSHOT_REQUESTED, False)
        if not already:
            self._session.set_context(session_id, CTX_THANK_YOU_SNAPSHOT_REQUESTED, True)
            await self._sender.send_tool_calls(
                session_id,
                [
                    MCPCommand(
                        tool_name="get_dom_snapshot",
                        arguments={"include_frames": False, "max_chars": 400000},
                        description="extract thank-you page info",
                    )
                ],
            )
        return True

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]) -> bool:
        if not self._sender or not self._session:
            return False

        tool_name = data.get("tool_name")
        result = data.get("result") or {}
        page_url = _resolve_page_url(self._session, session_id, data)

        if not _is_thank_you_url(page_url):
            return False

        info = _extract_thank_you_from_url(page_url)
        dom = result.get("dom") if isinstance(result, dict) else ""
        if tool_name == "get_dom_snapshot" and dom:
            dom_info = _extract_thank_you_from_dom(dom)
            for key, value in dom_info.items():
                if value:
                    info[key] = value

        if not info.get("order_id") and not info.get("price"):
            return True

        if _is_duplicate_order(self._session, session_id, info):
            return True

        _store_order_context(self._session, session_id, info)
        tts_text = _build_thank_you_tts(info)
        await self._sender.send_tts_response(session_id, tts_text)

        if not _is_order_detail_url(page_url):
            pending = self._session.get_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION)
            if not pending:
                self._session.set_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION, PENDING_ACTION_ORDER_DETAIL)
                await self._sender.send_tool_calls(
                    session_id,
                    [
                        MCPCommand(
                            tool_name="click",
                            arguments={"selector": SELECTOR_ORDER_DETAIL_BUTTON},
                            description="go to order detail",
                        )
                    ],
                )
        return True

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not text:
            return False

        session = self._session.get_session(session_id)
        current_url = session.current_url if session else ""

        if self._session.get_context(session_id, CTX_PAYMENT_POST_WAITING_ACTION):
            action = _resolve_follow_up_action(text)
            if not action:
                await self._sender.send_tts_response(
                    session_id,
                    "주문 상세보기 또는 쇼핑 계속하기 중에서 말씀해 주세요.",
                )
                return True

            self._session.set_context(session_id, CTX_PAYMENT_POST_WAITING_ACTION, False)
            if action == PENDING_ACTION_ORDER_DETAIL:
                if _is_order_detail_url(current_url):
                    return False
                self._session.set_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION, PENDING_ACTION_ORDER_DETAIL)
                await self._sender.send_tool_calls(
                    session_id,
                    [
                        MCPCommand(
                            tool_name="click",
                            arguments={"selector": SELECTOR_ORDER_DETAIL_BUTTON},
                            description="go to order detail",
                        )
                    ],
                )
                return True

            if action == PENDING_ACTION_MAIN:
                if _is_main_url(current_url):
                    await self._sender.send_tts_response(session_id, MAIN_PAGE_TTS)
                    return True
                self._session.set_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION, PENDING_ACTION_MAIN)
                await self._sender.send_tool_calls(
                    session_id,
                    [
                        MCPCommand(
                            tool_name="click",
                            arguments={"selector": SELECTOR_CONTINUE_SHOPPING_BUTTON},
                            description="continue shopping",
                        )
                    ],
                )
                return True

        return False

    def cleanup_session(self, session_id: str):
        if not self._session:
            return
        self._session.set_context(session_id, CTX_THANK_YOU_SNAPSHOT_REQUESTED, None)
        self._session.set_context(session_id, CTX_THANK_YOU_ORDER_ID, None)
        self._session.set_context(session_id, CTX_THANK_YOU_CHECKOUT_ID, None)
        self._session.set_context(session_id, CTX_PAYMENT_POST_WAITING_ACTION, None)
        self._session.set_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION, None)

    async def _handle_pending_action(self, session_id: str, current_url: str) -> bool:
        pending = self._session.get_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION)
        if not pending:
            return False
        if pending == PENDING_ACTION_MAIN and _is_main_url(current_url):
            self._session.set_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION, None)
            await self._sender.send_tts_response(session_id, MAIN_PAGE_TTS)
            return True
        if pending == PENDING_ACTION_ORDER_DETAIL and _is_order_detail_url(current_url):
            self._session.set_context(session_id, CTX_PAYMENT_POST_PENDING_ACTION, None)
            return True
        return False


def _resolve_page_url(session_manager, session_id: str, data: Dict[str, Any]) -> str:
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


def _is_thank_you_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        return "mc.coupang.com" in host and "/ssr/desktop/thank-you" in path
    except Exception:
        return False


def _is_order_detail_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        return "mc.coupang.com" in host and bool(re.search(r"/ssr/desktop/order/\d+", path))
    except Exception:
        return False


def _is_main_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").rstrip("/")
        if host in {"www.coupang.com", "coupang.com"} and path in {"", "/"}:
            return True
    except Exception:
        return False
    return False


def _extract_thank_you_from_url(url: str) -> Dict[str, Any]:
    if not url:
        return {}
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        order_id = (qs.get("orderId") or [""])[0]
        checkout_id = (qs.get("checkoutId") or [""])[0]
        price = (qs.get("price") or [""])[0]
        pay_type = (qs.get("payType") or [""])[0]
        return {
            "order_id": order_id.strip() if isinstance(order_id, str) else "",
            "checkout_id": checkout_id.strip() if isinstance(checkout_id, str) else "",
            "price": price.strip() if isinstance(price, str) else "",
            "pay_type": pay_type.strip() if isinstance(pay_type, str) else "",
        }
    except Exception:
        return {}


def _extract_next_data(dom: str) -> Optional[Dict[str, Any]]:
    if not dom:
        return None
    match = re.search(r"<script[^>]*id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>", dom, re.S)
    if not match:
        return None
    raw = html_lib.unescape(match.group(1) or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _extract_thank_you_from_dom(dom: str) -> Dict[str, Any]:
    data = _extract_next_data(dom)
    if not data:
        return {}
    try:
        thank_you = (
            data.get("props", {})
            .get("pageProps", {})
            .get("domains", {})
            .get("thankYou", {})
            .get("thankYouPageModel", {})
        )
        order = thank_you.get("order", {}) if isinstance(thank_you, dict) else {}
        payment = thank_you.get("payment", {}) if isinstance(thank_you, dict) else {}
        payed = payment.get("payedPayment", {}) if isinstance(payment, dict) else {}
        rocket_bank = payed.get("rocketBankPayment", {}) if isinstance(payed, dict) else {}
        return {
            "order_id": str(order.get("orderId") or ""),
            "title": order.get("title") or "",
            "price": payment.get("totalPayedAmount"),
            "pay_type": payment.get("mainPayType") or "",
            "bank_name": rocket_bank.get("bankName") or "",
            "paid_at": payment.get("paidAt"),
        }
    except Exception:
        return {}


def _format_won(value: Any) -> str:
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


def _format_pay_type(pay_type: str, bank_name: str = "") -> str:
    if not pay_type:
        return ""
    mapping = {
        "ROCKET_BANK": "로켓뱅크",
        "ROCKET_CARD": "로켓카드",
        "CARD": "카드",
        "PHONE": "휴대폰",
        "VIRTUAL_ACCOUNT": "가상계좌",
        "REALTIME_BANK_TRANSFER": "실시간 계좌이체",
    }
    label = mapping.get(pay_type, pay_type)
    if bank_name:
        return f"{bank_name} {label}"
    return label


def _build_thank_you_tts(info: Dict[str, Any]) -> str:
    title = info.get("title") or ""
    price = _format_won(info.get("price"))
    pay_type = _format_pay_type(info.get("pay_type") or "", info.get("bank_name") or "")

    parts = ["주문이 완료되었습니다."]
    if title:
        parts.append(f"상품명은 {title}입니다.")
    if price:
        parts.append(f"결제금액은 {price}입니다.")
    if pay_type:
        parts.append(f"결제수단은 {pay_type}입니다.")
    return " ".join(parts)


def _resolve_follow_up_action(text: str) -> Optional[str]:
    normalized = re.sub(r"\s+", "", text or "")
    if not normalized:
        return None
    if any(key in normalized for key in ["주문상세", "상세보기", "주문내역", "상세"]):
        return PENDING_ACTION_ORDER_DETAIL
    if any(key in normalized for key in ["쇼핑계속", "계속쇼핑", "계속하기", "쇼핑"]):
        return PENDING_ACTION_MAIN
    if "계속" in normalized:
        return PENDING_ACTION_MAIN
    return None


def _is_duplicate_order(session_manager, session_id: str, info: Dict[str, Any]) -> bool:
    if not session_manager:
        return False
    order_id = info.get("order_id") or ""
    checkout_id = info.get("checkout_id") or ""
    last_order_id = session_manager.get_context(session_id, CTX_THANK_YOU_ORDER_ID, "")
    last_checkout_id = session_manager.get_context(session_id, CTX_THANK_YOU_CHECKOUT_ID, "")
    if order_id and order_id == last_order_id:
        return True
    if checkout_id and checkout_id == last_checkout_id:
        return True
    return False


def _store_order_context(session_manager, session_id: str, info: Dict[str, Any]) -> None:
    if not session_manager:
        return
    session_manager.set_context(session_id, CTX_THANK_YOU_SNAPSHOT_REQUESTED, False)
    if info.get("order_id"):
        session_manager.set_context(session_id, CTX_THANK_YOU_ORDER_ID, info.get("order_id"))
    if info.get("checkout_id"):
        session_manager.set_context(session_id, CTX_THANK_YOU_CHECKOUT_ID, info.get("checkout_id"))
    session_manager.set_context(session_id, "last_order", info)


__all__ = [
    "PaymentPostHandler",
    "_is_thank_you_url",
    "_extract_thank_you_from_url",
    "_extract_thank_you_from_dom",
    "_build_thank_you_tts",
    "CTX_THANK_YOU_SNAPSHOT_REQUESTED",
    "CTX_THANK_YOU_ORDER_ID",
    "CTX_THANK_YOU_CHECKOUT_ID",
    "CTX_PAYMENT_POST_WAITING_ACTION",
    "CTX_PAYMENT_POST_PENDING_ACTION",
    "FOLLOW_UP_TTS",
    "MAIN_PAGE_TTS",
    "SELECTOR_ORDER_DETAIL_BUTTON",
    "SELECTOR_CONTINUE_SHOPPING_BUTTON",
]
