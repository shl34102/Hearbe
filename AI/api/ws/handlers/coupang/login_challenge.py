# -*- coding: utf-8 -*-
"""
Login challenge handler (Coupang pincode flow).

Handles the additional verification steps after login submit:
- method select page (/login/pincode/select)
- pincode input page (/login/pincode/input)
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

from core.interfaces import MCPCommand
from services.ocr.payment.pin_parser import PinParser

logger = logging.getLogger(__name__)

CTX_STAGE = "login_challenge_stage"
CTX_LAST_URL = "login_challenge_last_url"
CTX_PROMPT_TS = "login_challenge_prompt_ts"
CTX_METHOD = "login_challenge_method"

STAGE_SELECT = "select"
STAGE_INPUT = "input"

PROMPT_COOLDOWN_SEC = 6.0

PINCODE_INPUT_SELECTOR = "input.pincode-input__pincode-input-box__pincode"
PINCODE_NEXT_SELECTOR = "button.pincode-content__button.pincode-input__button"

METHOD_SMS_SELECTOR = "input.pincode-select__pincode-verification-type-sms"
METHOD_EMAIL_SELECTOR = "input.pincode-select__pincode-verification-type-email"
METHOD_SUBMIT_SELECTOR = "button.pincode-content__button.pincode-select__button"

TTS_PROMPT_CODE = "인증번호 6자리를 말씀해 주세요."
TTS_INVALID_CODE = "인증번호는 6자리여야 합니다. 다시 말씀해 주세요."


class LoginChallengeManager:
    def __init__(self, sender, session_manager, default_method: str = "SMS"):
        self._sender = sender
        self._session = session_manager
        self._parser = PinParser()
        self._default_method = (default_method or "SMS").upper()

    async def handle_page_update(self, session_id: str, url: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not url:
            return False

        if _is_pincode_select_url(url):
            await self._handle_select_page(session_id, url)
            return True

        if _is_pincode_input_url(url):
            await self._handle_input_page(session_id, url)
            return True

        return False

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not text:
            return False

        stage = self._session.get_context(session_id, CTX_STAGE)
        if stage != STAGE_INPUT:
            return False

        parsed = self._parser.parse(text)
        digits = parsed.digits
        if not digits:
            return False

        if len(digits) != 6:
            await self._sender.send_tts_response(session_id, TTS_INVALID_CODE)
            return True

        code = "".join(digits)
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": PINCODE_INPUT_SELECTOR},
                    description="focus pincode input",
                ),
                MCPCommand(
                    tool_name="fill",
                    arguments={"selector": PINCODE_INPUT_SELECTOR, "text": code},
                    description="fill pincode input",
                ),
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": PINCODE_NEXT_SELECTOR},
                    description="submit pincode",
                ),
            ],
        )
        return True

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_STAGE, None)
        self._session.set_context(session_id, CTX_LAST_URL, None)
        self._session.set_context(session_id, CTX_PROMPT_TS, None)
        self._session.set_context(session_id, CTX_METHOD, None)

    async def _handle_select_page(self, session_id: str, url: str) -> None:
        last_url = self._session.get_context(session_id, CTX_LAST_URL)
        if last_url == url and self._session.get_context(session_id, CTX_STAGE) == STAGE_SELECT:
            return

        self._session.set_context(session_id, CTX_STAGE, STAGE_SELECT)
        self._session.set_context(session_id, CTX_LAST_URL, url)

        method = self._session.get_context(session_id, CTX_METHOD) or self._default_method
        method = "EMAIL" if method == "EMAIL" else "SMS"
        self._session.set_context(session_id, CTX_METHOD, method)

        selector = METHOD_EMAIL_SELECTOR if method == "EMAIL" else METHOD_SMS_SELECTOR
        logger.info("login challenge: select method=%s selector=%s", method, selector)

        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": selector},
                    description=f"select {method} verification",
                ),
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": METHOD_SUBMIT_SELECTOR},
                    description="request verification code",
                ),
                MCPCommand(
                    tool_name="wait",
                    arguments={"ms": 800},
                    description="wait for pincode input page",
                ),
            ],
        )

    async def _handle_input_page(self, session_id: str, url: str) -> None:
        last_url = self._session.get_context(session_id, CTX_LAST_URL)
        if last_url == url and self._session.get_context(session_id, CTX_STAGE) == STAGE_INPUT:
            return

        self._session.set_context(session_id, CTX_STAGE, STAGE_INPUT)
        self._session.set_context(session_id, CTX_LAST_URL, url)

        now = time.time()
        last_prompt = self._session.get_context(session_id, CTX_PROMPT_TS)
        if last_prompt and now - float(last_prompt) < PROMPT_COOLDOWN_SEC:
            return
        self._session.set_context(session_id, CTX_PROMPT_TS, now)
        await self._sender.send_tts_response(session_id, TTS_PROMPT_CODE)


def _is_pincode_select_url(url: str) -> bool:
    return _match_host_path(url, "login.coupang.com", "/login/pincode/select")


def _is_pincode_input_url(url: str) -> bool:
    return _match_host_path(url, "login.coupang.com", "/login/pincode/input")


def _match_host_path(url: str, host: str, path_prefix: str) -> bool:
    try:
        parsed = urlparse(url)
        return host in (parsed.netloc or "").lower() and (parsed.path or "").startswith(path_prefix)
    except Exception:
        return False


__all__ = ["LoginChallengeManager"]
