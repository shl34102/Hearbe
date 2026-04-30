# -*- coding: utf-8 -*-
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "api" not in sys.modules:
    api_pkg = types.ModuleType("api")
    api_pkg.__path__ = [str(ROOT / "api")]
    sys.modules["api"] = api_pkg

from core.interfaces import SessionState
from api.ws.feedback.payment_post_handler import (
    PaymentPostHandler,
    _is_thank_you_url,
    _extract_thank_you_from_url,
    _extract_thank_you_from_dom,
    _build_thank_you_tts,
    CTX_THANK_YOU_SNAPSHOT_REQUESTED,
    CTX_THANK_YOU_ORDER_ID,
    CTX_THANK_YOU_CHECKOUT_ID,
    CTX_PAYMENT_POST_WAITING_ACTION,
    CTX_PAYMENT_POST_PENDING_ACTION,
    FOLLOW_UP_TTS,
    MAIN_PAGE_TTS,
    SELECTOR_ORDER_DETAIL_BUTTON,
)


class FakeSender:
    def __init__(self):
        self.tool_calls = []
        self.tts = []

    async def send_tool_calls(self, session_id, commands):
        self.tool_calls.append((session_id, commands))

    async def send_tts_response(self, session_id, text):
        self.tts.append((session_id, text))


class FakeSessionManager:
    def __init__(self, session):
        self._sessions = {session.session_id: session}

    def get_session(self, session_id):
        return self._sessions.get(session_id)

    def get_context(self, session_id, key, default=None):
        session = self._sessions.get(session_id)
        if not session:
            return default
        return session.context.get(key, default)

    def set_context(self, session_id, key, value):
        session = self._sessions.get(session_id)
        if not session:
            return
        session.context[key] = value


def _build_dom_with_next_data(payload: dict) -> str:
    return (
        "<html><head>"
        "<script id=\"__NEXT_DATA__\" type=\"application/json\">"
        + json.dumps(payload, ensure_ascii=False)
        + "</script>"
        "</head><body>ok</body></html>"
    )


def test_is_thank_you_url():
    assert _is_thank_you_url("https://mc.coupang.com/ssr/desktop/thank-you?orderId=1")
    assert not _is_thank_you_url("https://cart.coupang.com/cartView.pang")


def test_extract_thank_you_from_url():
    url = (
        "https://mc.coupang.com/ssr/desktop/thank-you?"
        "orderId=21100169768698&price=6390&payType=ROCKET_BANK&checkoutId=1770177202013"
    )
    info = _extract_thank_you_from_url(url)
    assert info["order_id"] == "21100169768698"
    assert info["price"] == "6390"
    assert info["pay_type"] == "ROCKET_BANK"
    assert info["checkout_id"] == "1770177202013"


def test_extract_thank_you_from_dom():
    payload = {
        "props": {
            "pageProps": {
                "domains": {
                    "thankYou": {
                        "thankYouPageModel": {
                            "order": {"orderId": 123, "title": "테스트 상품"},
                            "payment": {
                                "totalPayedAmount": 6390,
                                "mainPayType": "ROCKET_BANK",
                                "payedPayment": {"rocketBankPayment": {"bankName": "하나은행"}},
                            },
                        }
                    }
                }
            }
        }
    }
    dom = _build_dom_with_next_data(payload)
    info = _extract_thank_you_from_dom(dom)
    assert info["order_id"] == "123"
    assert info["title"] == "테스트 상품"
    assert info["price"] == 6390
    assert info["pay_type"] == "ROCKET_BANK"
    assert info["bank_name"] == "하나은행"


def test_build_thank_you_tts():
    info = {
        "order_id": "21100169768698",
        "title": "테스트 상품",
        "price": 6390,
        "pay_type": "ROCKET_BANK",
        "bank_name": "하나은행",
    }
    tts = _build_thank_you_tts(info)
    assert "주문이 완료되었습니다." in tts
    assert "6,390원" in tts
    assert "하나은행 로켓뱅크" in tts


@pytest.mark.asyncio
async def test_handle_page_update_requests_snapshot():
    session = SessionState(session_id="s1", current_url="https://mc.coupang.com/ssr/desktop/thank-you?orderId=1")
    sender = FakeSender()
    manager = PaymentPostHandler(sender=sender, session_manager=FakeSessionManager(session))

    handled = await manager.handle_page_update("s1", session.current_url)
    assert handled is True
    assert session.context.get(CTX_THANK_YOU_SNAPSHOT_REQUESTED) is True
    assert sender.tool_calls
    _, commands = sender.tool_calls[-1]
    assert commands[0].tool_name == "get_dom_snapshot"


@pytest.mark.asyncio
async def test_handle_mcp_result_sends_tts_and_sets_context():
    session = SessionState(session_id="s2", current_url="https://mc.coupang.com/ssr/desktop/thank-you?orderId=1&price=6390")
    sender = FakeSender()
    manager = PaymentPostHandler(sender=sender, session_manager=FakeSessionManager(session))

    payload = {
        "props": {
            "pageProps": {
                "domains": {
                    "thankYou": {
                        "thankYouPageModel": {
                            "order": {"orderId": 21100169768698, "title": "테스트 상품"},
                            "payment": {
                                "totalPayedAmount": 6390,
                                "mainPayType": "ROCKET_BANK",
                                "payedPayment": {"rocketBankPayment": {"bankName": "하나은행"}},
                            },
                        }
                    }
                }
            }
        }
    }
    dom = _build_dom_with_next_data(payload)

    handled = await manager.handle_mcp_result(
        "s2",
        {
            "tool_name": "get_dom_snapshot",
            "success": True,
            "result": {"dom": dom, "page_url": session.current_url},
        },
    )
    assert handled is True
    assert sender.tts

    # Follow-up question is removed; we auto-navigate to order detail.
    assert not any(FOLLOW_UP_TTS in text for _, text in sender.tts)
    assert sender.tool_calls
    _, commands = sender.tool_calls[-1]
    assert commands[0].tool_name == "click"
    assert session.context.get(CTX_THANK_YOU_ORDER_ID) == "21100169768698"
    assert session.context.get(CTX_THANK_YOU_CHECKOUT_ID) is None


@pytest.mark.asyncio
async def test_handle_user_text_selects_order_detail():
    session = SessionState(session_id="s3", current_url="https://mc.coupang.com/ssr/desktop/thank-you?orderId=1")
    session.context[CTX_PAYMENT_POST_WAITING_ACTION] = True
    sender = FakeSender()
    manager = PaymentPostHandler(sender=sender, session_manager=FakeSessionManager(session))

    handled = await manager.handle_user_text("s3", "주문 상세보기")
    assert handled is True
    assert sender.tool_calls
    _, commands = sender.tool_calls[-1]
    assert commands[0].arguments.get("selector") == SELECTOR_ORDER_DETAIL_BUTTON
    assert session.context.get(CTX_PAYMENT_POST_PENDING_ACTION) == "order_detail"


@pytest.mark.asyncio
async def test_handle_page_update_main_page_tts():
    session = SessionState(session_id="s4", current_url="https://mc.coupang.com/ssr/desktop/thank-you?orderId=1")
    session.context[CTX_PAYMENT_POST_PENDING_ACTION] = "main"
    sender = FakeSender()
    manager = PaymentPostHandler(sender=sender, session_manager=FakeSessionManager(session))

    handled = await manager.handle_page_update("s4", "https://www.coupang.com/")
    assert handled is True
    assert sender.tts
    assert sender.tts[-1][1] == MAIN_PAGE_TTS
