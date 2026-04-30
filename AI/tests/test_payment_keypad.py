# -*- coding: utf-8 -*-
import base64
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
from api.ws.handlers.coupang.payment_keypad import (
    PaymentKeypadManager,
    CTX_ARMED,
    CTX_WAIT_ARGS,
    CTX_PENDING_DIGITS,
    CTX_AWAITING,
    CTX_MAPPING,
    CTX_READY,
)
from api.ws.presenter.pages.checkout import KEYPAD_PROMPT


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


@pytest.mark.asyncio
async def test_digit_input_triggers_keypad_detection_on_checkout():
    session = SessionState(
        session_id="s1",
        current_url="https://checkout.coupang.com",
    )
    sender = FakeSender()
    manager = PaymentKeypadManager(sender=sender, session_manager=FakeSessionManager(session))

    # PIN is 6 digits (2nd password). Shorter inputs should be rejected.
    handled = await manager.handle_user_text("s1", "587000")
    assert handled is True
    assert session.context.get(CTX_ARMED) is True
    assert session.context.get(CTX_PENDING_DIGITS) == ["5", "8", "7", "0", "0", "0"]
    assert sender.tool_calls
    _, commands = sender.tool_calls[-1]
    assert commands[0].tool_name == "wait_for_selector"


@pytest.mark.asyncio
async def test_wait_for_selector_success_prompts_and_requests_assets():
    session = SessionState(
        session_id="s2",
        current_url="https://checkout.coupang.com",
    )
    sender = FakeSender()
    manager = PaymentKeypadManager(sender=sender, session_manager=FakeSessionManager(session))

    wait_args = {
        "selector": ".pad",
        "state": "visible",
        "timeout": 60000,
        "frame_selector": "iframe[src*='payment.coupang.com/v4/payments/payment']",
    }
    session.context[CTX_ARMED] = True
    session.context[CTX_WAIT_ARGS] = wait_args

    handled = await manager.handle_mcp_result(
        "s2",
        {
            "tool_name": "wait_for_selector",
            "arguments": wait_args,
            "success": True,
            "result": {"element_found": True},
        },
    )
    assert handled is True
    assert session.context.get(CTX_AWAITING) is True
    assert any(text == KEYPAD_PROMPT for _, text in sender.tts)
    assert sender.tool_calls
    _, commands = sender.tool_calls[-1]
    assert len(commands) == 2
    assert {cmd.tool_name for cmd in commands} == {"get_attribute_list", "screenshot_element"}


@pytest.mark.asyncio
async def test_ocr_mapping_sets_context(monkeypatch):
    session = SessionState(
        session_id="s3",
        current_url="https://checkout.coupang.com",
    )
    sender = FakeSender()
    manager = PaymentKeypadManager(sender=sender, session_manager=FakeSessionManager(session))

    def fake_map_keypad_image(image_bytes, dom_keys, device="cpu"):
        return {
            "digits": ["0", "1"],
            "dom_keys": dom_keys,
            "digit_to_key_mapping": {"0": "0", "1": "1"},
        }

    fake_module = types.ModuleType("services.ocr.payment.keypad_mapper")
    fake_module.map_keypad_image = fake_map_keypad_image
    fake_module.is_ocr_instance_ready = lambda: True
    monkeypatch.setitem(sys.modules, "services.ocr.payment.keypad_mapper", fake_module)

    # Avoid triggering the "empty_or_small_image" guard in the handler.
    shot_b64 = base64.b64encode(b"x" * 2048).decode("utf-8")
    await manager._run_ocr("s3", shot_b64, ["0", "1"])

    assert session.context.get(CTX_MAPPING) == {"0": "0", "1": "1"}
    assert session.context.get(CTX_READY) is True
