# -*- coding: utf-8 -*-
"""
Payment keypad manager.

Detects keypad iframe on checkout page, runs OCR to map digits to DOM keys,
prompts for PIN via TTS, and clicks mapped keys on spoken input.
"""

import asyncio
import base64
import logging
import os
from typing import Dict, Any, Optional, List

from core.interfaces import MCPCommand
from services.ocr.payment.pin_parser import PinParser
from services.llm.sites.site_manager import get_page_type, get_selector
from ...presenter.pages.checkout import (
    KEYPAD_PROMPT,
    KEYPAD_RETRY,
    KEYPAD_LENGTH_INVALID,
    KEYPAD_NOT_READY,
    KEYPAD_FAIL,
    KEYPAD_FAIL_SIMPLE,
    KEYPAD_IMAGE_UNREADABLE,
)
from ...feedback.payment_post_handler import PaymentPostHandler

logger = logging.getLogger(__name__)


DEFAULT_KEYPAD_SELECTOR = ".pad"
DEFAULT_FRAME_SELECTOR = "iframe[src*='payment.coupang.com/v4/payments/payment']"
DEFAULT_KEY_SELECTOR_TEMPLATE = "a.pad-key[data-key='{key}']"

CTX_WAIT_ARGS = "payment_keypad_wait_args"
CTX_DOMKEYS_ARGS = "payment_keypad_domkeys_args"
CTX_SCREENSHOT_ARGS = "payment_keypad_screenshot_args"
CTX_DOM_KEYS = "payment_keypad_dom_keys"
CTX_MAPPING = "payment_keypad_mapping"
CTX_READY = "payment_keypad_ready"
CTX_AWAITING = "payment_keypad_awaiting_pin"
CTX_PROMPTED = "payment_keypad_prompted"
CTX_FRAME_SELECTOR = "payment_keypad_frame_selector"
CTX_LAST_URL = "payment_keypad_last_url"
CTX_ARMED = "payment_keypad_armed"
CTX_PENDING_DIGITS = "payment_keypad_pending_digits"




class PaymentKeypadManager:
    """Orchestrates keypad detection and PIN entry on checkout page."""

    def __init__(self, sender, session_manager):
        self._sender = sender
        self._session = session_manager
        self._ocr_tasks: Dict[str, asyncio.Task] = {}
        self._post_handler = PaymentPostHandler(sender, session_manager)

    async def handle_page_update(self, session_id: str, current_url: str):
        """Reset or trigger detection when page changes."""
        if not current_url:
            return
        await self._post_handler.handle_page_update(session_id, current_url)
        if get_page_type(current_url) != "checkout":
            self._reset_session(session_id, keep_armed=False)
            return

        armed = bool(self._get_context(session_id, CTX_ARMED))
        last_url = self._get_context(session_id, CTX_LAST_URL)
        if last_url and last_url != current_url:
            self._reset_session(session_id, keep_armed=armed)
        self._set_context(session_id, CTX_LAST_URL, current_url)
        if not self._get_context(session_id, CTX_ARMED):
            return
        await self._maybe_trigger_detection(session_id, current_url)

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Handle MCP results related to keypad detection/capture."""
        tool_name = data.get("tool_name")
        arguments = data.get("arguments") or {}
        success = bool(data.get("success"))
        result = data.get("result") or {}

        if tool_name in ("click", "click_element", "click_text") and success:
            current_url = _resolve_current_url(self._session, session_id, data)
            if _is_checkout_pay_action(current_url, tool_name, arguments):
                self._set_context(session_id, CTX_ARMED, True)
                if current_url:
                    self._set_context(session_id, CTX_LAST_URL, current_url)
                await self._maybe_trigger_detection(session_id, current_url)

        wait_args = self._get_context(session_id, CTX_WAIT_ARGS)
        if wait_args and tool_name == "wait_for_selector" and _args_match(wait_args, arguments):
            self._set_context(session_id, CTX_WAIT_ARGS, None)
            if not self._get_context(session_id, CTX_ARMED):
                return True
            if success and result.get("element_found"):
                if not self._get_context(session_id, CTX_PROMPTED):
                    await self._sender.send_tts_response(session_id, KEYPAD_PROMPT)
                    self._set_context(session_id, CTX_PROMPTED, True)
                self._set_context(session_id, CTX_AWAITING, True)
                await self._request_keypad_assets(session_id, wait_args)
                return True

            self._reset_session(session_id, keep_armed=False)
            await self._sender.send_tts_response(
                session_id,
                "키패드를 찾지 못했습니다. 결제하기 버튼을 다시 눌러주세요.",
            )
            return True

        dom_args = self._get_context(session_id, CTX_DOMKEYS_ARGS)
        if dom_args and tool_name == "get_attribute_list" and _args_match(dom_args, arguments):
            self._set_context(session_id, CTX_DOMKEYS_ARGS, None)
            values = result.get("values") if isinstance(result, dict) else None
            if values:
                self._set_context(session_id, CTX_DOM_KEYS, values)
            await self._maybe_start_ocr(session_id)
            return True

        shot_args = self._get_context(session_id, CTX_SCREENSHOT_ARGS)
        if shot_args and tool_name == "screenshot_element" and _args_match(shot_args, arguments):
            self._set_context(session_id, CTX_SCREENSHOT_ARGS, None)
            shot_b64 = result.get("screenshot_base64") if isinstance(result, dict) else None
            if shot_b64:
                self._set_context(session_id, "payment_keypad_screenshot", shot_b64)
            await self._maybe_start_ocr(session_id)
            return True

        handled = await self._post_handler.handle_mcp_result(session_id, data)
        if handled:
            return True
        return False

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        """Consume PIN input if keypad is awaiting digits."""
        current_url = ""
        if self._session:
            session = self._session.get_session(session_id)
            current_url = session.current_url if session else ""
        stage = bool(
            self._get_context(session_id, CTX_ARMED)
            or self._get_context(session_id, CTX_WAIT_ARGS)
            or self._get_context(session_id, CTX_DOMKEYS_ARGS)
            or self._get_context(session_id, CTX_SCREENSHOT_ARGS)
            or self._get_context(session_id, CTX_READY)
            or self._get_context(session_id, CTX_AWAITING)
            or self._get_context(session_id, CTX_FRAME_SELECTOR)
            or self._get_context(session_id, CTX_MAPPING)
            or self._get_context(session_id, CTX_PENDING_DIGITS)
        )
        digits = _extract_digits(text)
        if not stage:
            handled = await self._post_handler.handle_user_text(session_id, text)
            if handled:
                return True
            if digits and current_url and get_page_type(current_url) == "checkout":
                self._set_context(session_id, CTX_ARMED, True)
                if len(digits) != 6:
                    await self._sender.send_tts_response(session_id, KEYPAD_LENGTH_INVALID)
                    return True
                self._set_context(session_id, CTX_PENDING_DIGITS, digits)
                self._set_context(session_id, CTX_LAST_URL, current_url)
                await self._maybe_trigger_detection(session_id, current_url)
                return True
            return False

        if not digits:
            if self._get_context(session_id, CTX_AWAITING):
                await self._sender.send_tts_response(session_id, KEYPAD_RETRY)
            return True
        if len(digits) != 6:
            self._set_context(session_id, CTX_PENDING_DIGITS, None)
            await self._sender.send_tts_response(session_id, KEYPAD_LENGTH_INVALID)
            return True

        mapping = self._get_context(session_id, CTX_MAPPING) or {}
        if not mapping:
            self._set_context(session_id, CTX_PENDING_DIGITS, digits)
            if self._get_context(session_id, CTX_AWAITING) and not self._get_context(session_id, CTX_PROMPTED):
                await self._sender.send_tts_response(session_id, KEYPAD_NOT_READY)
            return True

        await self._send_keypad_clicks(session_id, digits, mapping)

        self._set_context(session_id, CTX_PENDING_DIGITS, None)
        self._set_context(session_id, CTX_AWAITING, False)
        return True

    def cleanup_session(self, session_id: str):
        self._reset_session(session_id, keep_armed=False)
        self._post_handler.cleanup_session(session_id)

    async def _maybe_trigger_detection(self, session_id: str, current_url: str):
        if not self._get_context(session_id, CTX_ARMED):
            return
        if self._get_context(session_id, CTX_READY) or self._get_context(session_id, CTX_WAIT_ARGS):
            return

        selector = get_selector(current_url, "keypad_container") or DEFAULT_KEYPAD_SELECTOR
        frame_selector = get_selector(current_url, "keypad_frame") or DEFAULT_FRAME_SELECTOR

        args = {
            "selector": selector,
            "state": "visible",
            "timeout": 60000,
            "frame_selector": frame_selector,
        }
        self._set_context(session_id, CTX_WAIT_ARGS, args)
        self._set_context(session_id, CTX_FRAME_SELECTOR, frame_selector)

        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="wait_for_selector",
                    arguments=args,
                    description="wait for payment keypad",
                )
            ],
        )

    async def _request_keypad_assets(self, session_id: str, wait_args: Dict[str, Any]):
        selector = wait_args.get("selector") or DEFAULT_KEYPAD_SELECTOR
        frame_selector = wait_args.get("frame_selector")
        self._set_context(session_id, CTX_FRAME_SELECTOR, frame_selector)

        dom_args = {
            "selector": f"{selector} a.pad-key",
            "attribute": "data-key",
        }
        if frame_selector:
            dom_args["frame_selector"] = frame_selector
        shot_args = {
            "selector": selector,
        }
        if frame_selector:
            shot_args["frame_selector"] = frame_selector

        self._set_context(session_id, CTX_DOMKEYS_ARGS, dom_args)
        self._set_context(session_id, CTX_SCREENSHOT_ARGS, shot_args)

        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="get_attribute_list",
                    arguments=dom_args,
                    description="collect keypad dom keys",
                ),
                MCPCommand(
                    tool_name="screenshot_element",
                    arguments=shot_args,
                    description="capture keypad image",
                ),
            ],
        )

    async def _maybe_start_ocr(self, session_id: str):
        if self._ocr_tasks.get(session_id):
            return
        dom_keys = self._get_context(session_id, CTX_DOM_KEYS)
        shot_b64 = self._get_context(session_id, "payment_keypad_screenshot")
        if not shot_b64:
            return
        if not dom_keys and self._get_context(session_id, CTX_DOMKEYS_ARGS):
            return
        if not dom_keys:
            dom_keys = [str(i) for i in range(10)]

        task = asyncio.create_task(self._run_ocr(session_id, shot_b64, dom_keys))
        self._ocr_tasks[session_id] = task

    async def _run_ocr(self, session_id: str, shot_b64: str, dom_keys: List[str]):
        frame_selector = self._get_context(session_id, CTX_FRAME_SELECTOR)
        try:
            image_bytes = base64.b64decode(shot_b64)
        except Exception as e:
            logger.error(
                "Keypad OCR failed: cause=invalid_base64 error=%s frame_selector=%s dom_keys=%d",
                e,
                frame_selector,
                len(dom_keys or []),
            )
            await self._sender.send_tts_response(session_id, KEYPAD_IMAGE_UNREADABLE)
            self._ocr_tasks.pop(session_id, None)
            return
        if not image_bytes or len(image_bytes) < 1024:
            logger.error(
                "Keypad OCR failed: cause=empty_or_small_image bytes=%d frame_selector=%s dom_keys=%d",
                len(image_bytes or b""),
                frame_selector,
                len(dom_keys or []),
            )
            await self._sender.send_tts_response(session_id, KEYPAD_IMAGE_UNREADABLE)
            self._ocr_tasks.pop(session_id, None)
            return

        device = os.getenv("OCR_DEVICE", "cpu")
        try:
            from services.ocr.payment.keypad_mapper import map_keypad_image, is_ocr_instance_ready
            logger.info(
                "Keypad OCR start: device=%s bytes=%d dom_keys=%d frame_selector=%s ocr_ready=%s",
                device,
                len(image_bytes),
                len(dom_keys or []),
                frame_selector,
                is_ocr_instance_ready(),
            )
            result = await asyncio.to_thread(map_keypad_image, image_bytes, dom_keys, device)
        except Exception as e:
            logger.error(
                "Keypad OCR failed: cause=exception type=%s error=%s frame_selector=%s",
                type(e).__name__,
                e,
                frame_selector,
            )
            await self._sender.send_tts_response(session_id, KEYPAD_FAIL_SIMPLE)
            self._ocr_tasks.pop(session_id, None)
            return

        mapping = result.get("digit_to_key_mapping") if isinstance(result, dict) else None
        if not mapping:
            logger.error(
                "Keypad OCR failed: cause=no_mapping digits=%s dom_keys=%s frame_selector=%s",
                result.get("digits") if isinstance(result, dict) else None,
                result.get("dom_keys") if isinstance(result, dict) else None,
                frame_selector,
            )
            await self._sender.send_tts_response(session_id, KEYPAD_FAIL_SIMPLE)
            self._ocr_tasks.pop(session_id, None)
            return

        self._set_context(session_id, CTX_MAPPING, mapping)
        self._set_context(session_id, CTX_ARMED, False)
        self._set_context(session_id, CTX_READY, True)
        logger.info(
            "Keypad OCR mapping ready: digits=%s dom_keys=%s mapping=%s",
            result.get("digits"),
            result.get("dom_keys"),
            mapping,
        )
        pending_digits = self._get_context(session_id, CTX_PENDING_DIGITS)
        if pending_digits:
            await self._send_keypad_clicks(session_id, pending_digits, mapping)
            self._set_context(session_id, CTX_PENDING_DIGITS, None)
            self._set_context(session_id, CTX_AWAITING, False)
            self._set_context(session_id, CTX_PROMPTED, True)
            self._ocr_tasks.pop(session_id, None)
            return
        if not self._get_context(session_id, CTX_PROMPTED):
            await self._sender.send_tts_response(session_id, KEYPAD_PROMPT)
            self._set_context(session_id, CTX_PROMPTED, True)
        self._set_context(session_id, CTX_AWAITING, True)
        self._ocr_tasks.pop(session_id, None)

    async def _send_keypad_clicks(
        self,
        session_id: str,
        digits: List[str],
        mapping: Dict[str, str],
    ) -> bool:
        frame_selector = self._get_context(session_id, CTX_FRAME_SELECTOR)
        commands: List[MCPCommand] = []
        for digit in digits:
            key = mapping.get(digit)
            if key is None:
                await self._sender.send_tts_response(session_id, KEYPAD_FAIL)
                return False
            selector = _get_key_selector(self._get_context(session_id, CTX_LAST_URL), key)
            args = {"selector": selector}
            if frame_selector:
                args["frame_selector"] = frame_selector
            commands.append(
                MCPCommand(
                    tool_name="click_element",
                    arguments=args,
                    description=f"keypad click {digit}",
                )
            )

        if commands:
            await self._sender.send_tool_calls(session_id, commands)
        return True

    def _reset_session(self, session_id: str, keep_armed: bool = False):
        task = self._ocr_tasks.pop(session_id, None)
        if task:
            task.cancel()
        self._set_context(session_id, CTX_WAIT_ARGS, None)
        self._set_context(session_id, CTX_DOMKEYS_ARGS, None)
        self._set_context(session_id, CTX_SCREENSHOT_ARGS, None)
        self._set_context(session_id, CTX_DOM_KEYS, None)
        self._set_context(session_id, CTX_MAPPING, None)
        self._set_context(session_id, CTX_READY, False)
        self._set_context(session_id, CTX_AWAITING, False)
        self._set_context(session_id, CTX_PROMPTED, False)
        self._set_context(session_id, CTX_FRAME_SELECTOR, None)
        self._set_context(session_id, "payment_keypad_screenshot", None)
        self._set_context(session_id, CTX_LAST_URL, None)
        self._set_context(session_id, CTX_PENDING_DIGITS, None)
        if not keep_armed:
            self._set_context(session_id, CTX_ARMED, False)

    def _get_context(self, session_id: str, key: str, default=None):
        if not self._session:
            return default
        return self._session.get_context(session_id, key, default)

    def _set_context(self, session_id: str, key: str, value):
        if not self._session:
            return
        self._session.set_context(session_id, key, value)


def _resolve_current_url(session_manager, session_id: str, data: Dict[str, Any]) -> str:
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


def _is_checkout_pay_action(current_url: str, tool_name: str, arguments: Dict[str, Any]) -> bool:
    if not current_url or get_page_type(current_url) != "checkout":
        return False
    args = arguments or {}
    pay_selector = get_selector(current_url, "pay_button")
    if tool_name in ("click", "click_element"):
        selector = (args.get("selector") or "").strip()
        if not selector:
            return False
        if pay_selector and selector == pay_selector:
            return True
        if "결제" in selector:
            return True
        return False
    if tool_name == "click_text":
        text = (args.get("text") or "").strip()
        if not text:
            return False
        return "결제" in text or "주문" in text
    return False


def _args_match(expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    if not expected:
        return False
    if not actual:
        return False
    for key, value in expected.items():
        if actual.get(key) != value:
            return False
    return True



def _extract_digits(text: str) -> List[str]:
    result = PinParser().parse(text or "")
    return result.digits


def _get_key_selector(current_url: Optional[str], key: str) -> str:
    if current_url:
        selector = get_selector(current_url, f"keypad_key_{key}")
        if selector:
            return selector
    return DEFAULT_KEY_SELECTOR_TEMPLATE.format(key=key)
