# -*- coding: utf-8 -*-
"""
Login status handler.

Checks whether the user is already logged in before running login actions.
If logged in, respond immediately; otherwise re-queue the original text.
"""

import logging
import re
import time
from typing import Optional

from core.interfaces import MCPCommand

logger = logging.getLogger(__name__)

CTX_PENDING = "login_status_pending"
CTX_TEXT = "login_status_text"
CTX_SKIP_ONCE = "login_status_skip_once"
CTX_LAST_TS = "login_status_last_ts"

SKIP_WINDOW_SEC = 3.0


class LoginStatusManager:
    def __init__(self, sender, session_manager, enqueue_text=None):
        self._sender = sender
        self._session = session_manager
        self._enqueue_text = enqueue_text

    def set_enqueue(self, enqueue_text):
        self._enqueue_text = enqueue_text

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        if not self._session:
            return False
        if not _is_login_intent(text):
            return False

        if self._session.get_context(session_id, CTX_SKIP_ONCE):
            self._session.set_context(session_id, CTX_SKIP_ONCE, None)
            return False

        if self._session.get_context(session_id, CTX_PENDING):
            return True

        last_ts = self._session.get_context(session_id, CTX_LAST_TS)
        if last_ts and time.time() - float(last_ts) < SKIP_WINDOW_SEC:
            return False

        self._session.set_context(session_id, CTX_PENDING, True)
        self._session.set_context(session_id, CTX_TEXT, text)
        self._session.set_context(session_id, CTX_LAST_TS, time.time())

        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="check_login_status",
                    arguments={},
                    description="check login status for login intent",
                )
            ],
        )
        return True

    async def handle_mcp_result(self, session_id: str, data: dict) -> bool:
        tool_name = data.get("tool_name")
        if tool_name != "check_login_status":
            return False
        if not self._session:
            return False

        if not self._session.get_context(session_id, CTX_PENDING):
            return False

        result = data.get("result") or {}
        logged_in = result.get("logged_in")
        self._session.set_context(session_id, CTX_PENDING, None)

        if logged_in is True:
            logger.info("login status: already logged in (session=%s)", session_id)
            await self._sender.send_tts_response(
                session_id,
                "이미 로그인되어 있습니다. 다른 요청을 말씀해 주세요.",
            )
            return True

        original_text = self._session.get_context(session_id, CTX_TEXT) or ""
        self._session.set_context(session_id, CTX_TEXT, None)
        self._session.set_context(session_id, CTX_SKIP_ONCE, True)

        if self._enqueue_text and original_text:
            await self._enqueue_text(session_id, original_text)
            return True

        return False

    def cleanup_session(self, session_id: str):
        if not self._session:
            return
        self._session.set_context(session_id, CTX_PENDING, None)
        self._session.set_context(session_id, CTX_TEXT, None)
        self._session.set_context(session_id, CTX_SKIP_ONCE, None)
        self._session.set_context(session_id, CTX_LAST_TS, None)


def _is_login_intent(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "로그인" not in text and "login" not in lowered:
        return False
    if "로그아웃" in text or "logout" in lowered:
        return False
    # Avoid OTP / phone-only inputs.
    digits = re.sub(r"\\D", "", text)
    if 4 <= len(digits) <= 8 and "로그인" not in text:
        return False
    return True
