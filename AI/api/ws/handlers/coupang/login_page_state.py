# -*- coding: utf-8 -*-
"""
Login page state handler.

Detects which login method tab is active on Coupang login page and
announces a basic guidance TTS. Stores the active method in session context
for LLM prompt guidance.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from services.llm.generators.tts_generator import TTSGenerator
from services.llm.sites.site_manager import get_page_type

logger = logging.getLogger(__name__)

CTX_GUIDANCE_PENDING = "login_page_guidance_pending"
CTX_GUIDANCE_SENT = "login_page_guidance_sent"
CTX_GUIDANCE_PAGE = "login_page_guidance_page"
CTX_AUTOFILL_PENDING = "login_autofill_pending"
CTX_AUTOFILL_FINALIZED = "login_autofill_finalized"
CTX_AUTOFILL_USED = "login_autofill_used"
CTX_LOGOUT_SUPPRESS_UNTIL = "logout_guidance_suppress_until"


class LoginPageStateManager:
    def __init__(self, sender, session_manager):
        self._sender = sender
        self._session = session_manager
        self._tts = TTSGenerator()

    async def handle_page_update(self, session_id: str, url: str, previous_url: Optional[str] = None, page_id: Optional[str] = None) -> bool:
        if not self._sender or not self._session:
            return False
        page_type = get_page_type(url)
        if page_type != "login":
            return False
        if not _is_coupang_login_url(url):
            return False

        # Avoid re-announcing on same page id or same url bounce.
        page_key = str(page_id or url)
        if self._session.get_context(session_id, CTX_GUIDANCE_SENT) == page_key:
            return False
        if not self._should_defer_guidance(session_id):
            await self._send_guidance(session_id)
            self._session.set_context(session_id, CTX_GUIDANCE_SENT, page_key)
        else:
            self._session.set_context(session_id, CTX_GUIDANCE_PENDING, True)
            self._session.set_context(session_id, CTX_GUIDANCE_PAGE, page_key)
        return True

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]) -> bool:
        return False

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_GUIDANCE_PENDING, None)
        self._session.set_context(session_id, CTX_GUIDANCE_SENT, None)
        self._session.set_context(session_id, CTX_GUIDANCE_PAGE, None)

    async def _send_guidance(self, session_id: str) -> None:
        await self._sender.send_tts_response(session_id, self._tts.build_login_guidance())

    def _should_defer_guidance(self, session_id: str) -> bool:
        pending = bool(self._session.get_context(session_id, CTX_AUTOFILL_PENDING))
        finalized = bool(self._session.get_context(session_id, CTX_AUTOFILL_FINALIZED))
        if pending and not finalized:
            return True
        used = bool(self._session.get_context(session_id, CTX_AUTOFILL_USED))
        if used:
            # Autofill already used; do not speak extra login guidance.
            return True
        until = self._session.get_context(session_id, CTX_LOGOUT_SUPPRESS_UNTIL, 0)
        if until:
            try:
                if time.time() < float(until):
                    return True
            except Exception:
                return True
        return False

def _is_coupang_login_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return "login.coupang.com" in lowered and "/login/login.pang" in lowered


__all__ = ["LoginPageStateManager"]
