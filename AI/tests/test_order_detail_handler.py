# -*- coding: utf-8 -*-
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
from services.llm.generators.llm_generator import LLMResult
from api.ws.feedback.order_detail_handler import (
    OrderDetailHandler,
    ORDER_DETAIL_PROMPT,
    ORDER_DETAIL_NOT_FOUND_TTS,
    CTX_ORDER_DETAIL_DATA,
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


class FakeLLM:
    def __init__(self, response_text="응답"):
        self.response_text = response_text
        self.messages = []

    async def generate_with_messages(self, messages, current_url=""):
        self.messages.append((messages, current_url))
        return LLMResult(commands=[], response_text=self.response_text, success=True)


def _sample_order_detail():
    return {
        "order": {"order_id": 21100169768698, "title": "테스트 상품"},
        "items": [{"product_name": "테스트 상품", "quantity": 1}],
        "payment": {"total_payed_amount": 6390},
        "actions": ["장바구니 담기", "배송 조회"],
        "text": {"status": "배송중"},
    }


@pytest.mark.asyncio
async def test_handle_page_update_triggers_extract_and_announces():
    order_url = "https://mc.coupang.com/ssr/desktop/order/21100169768698"
    session = SessionState(session_id="s1", current_url=order_url)
    sender = FakeSender()
    manager = OrderDetailHandler(sender=sender, session_manager=FakeSessionManager(session))

    handled = await manager.handle_page_update("s1", order_url)
    assert handled is True
    assert sender.tool_calls

    handled = await manager.handle_mcp_result(
        "s1",
        {
            "tool_name": "extract_order_detail",
            "success": True,
            "result": {"order_detail": _sample_order_detail(), "page_url": order_url},
        },
    )
    assert handled is True
    assert sender.tts
    assert any(ORDER_DETAIL_PROMPT in text for _, text in sender.tts)
    assert session.context.get(CTX_ORDER_DETAIL_DATA)


@pytest.mark.asyncio
async def test_handle_user_question_uses_llm():
    order_url = "https://mc.coupang.com/ssr/desktop/order/21100169768698"
    session = SessionState(session_id="s2", current_url=order_url)
    sender = FakeSender()
    fake_llm = FakeLLM("배송 상태는 준비중입니다.")
    manager = OrderDetailHandler(sender=sender, session_manager=FakeSessionManager(session), llm_generator=fake_llm)

    handled = await manager.handle_user_text("s2", "배송 상태 알려줘")
    assert handled is True
    assert sender.tool_calls

    handled = await manager.handle_mcp_result(
        "s2",
        {
            "tool_name": "extract_order_detail",
            "success": True,
            "result": {"order_detail": _sample_order_detail(), "page_url": order_url},
        },
    )
    assert handled is True
    assert sender.tts
    assert sender.tts[-1][1] == "배송 상태는 준비중입니다."
    assert fake_llm.messages


@pytest.mark.asyncio
async def test_order_detail_no_question_returns_default():
    order_url = "https://mc.coupang.com/ssr/desktop/order/21100169768698"
    session = SessionState(session_id="s3", current_url=order_url)
    sender = FakeSender()
    fake_llm = FakeLLM("")
    manager = OrderDetailHandler(sender=sender, session_manager=FakeSessionManager(session), llm_generator=fake_llm)

    handled = await manager.handle_user_text("s3", "")
    assert handled is False

    handled = await manager.handle_user_text("s3", "결제 얼마야")
    assert handled is True
    assert sender.tool_calls

    handled = await manager.handle_mcp_result(
        "s3",
        {
            "tool_name": "extract_order_detail",
            "success": True,
            "result": {"order_detail": {}, "page_url": order_url},
        },
    )
    assert handled is True
    assert sender.tts
    assert sender.tts[-1][1] in [ORDER_DETAIL_NOT_FOUND_TTS, ""]
