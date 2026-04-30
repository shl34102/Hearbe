# -*- coding: utf-8 -*-
"""
Hearbe session gate.

Keep Hearbe auth/session routing separate from Coupang login autofill logic.

Responsibilities:
- On Hearbe /main entry:
  - call get_user_session
  - if logged in: redirect to the appropriate mall (/A|B|C/mall)
  - if not logged in: stay on /main and announce mode selection guidance TTS
- On Hearbe /A|B|C/login entry:
  - call get_user_session
  - if logged in: redirect to the appropriate mall
  - if not logged in: do nothing (stay on login)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from core.interfaces import MCPCommand
from services.llm.generators.tts_generator import TTSGenerator
from services.llm.sites.site_manager import get_current_site, get_page_type

logger = logging.getLogger(__name__)


CTX_SESSION_CHECK_PENDING = "hearbe_session_check_pending"
CTX_SESSION_CHECK_URL = "hearbe_session_check_url"
CTX_SESSION_CHECK_SOURCE = "hearbe_session_check_source"
CTX_SESSION_CHECK_PREVIOUS_URL = "hearbe_session_check_previous_url"

# When /main detects an existing session, we redirect to /A|B|C/mall.
# The mall page already announces a guidance TTS on page entry; emitting an additional
# "already logged in" TTS here causes duplication. We store a short-lived marker so
# the mall guidance can optionally include login status in a single TTS.
CTX_RECENT_LOGIN_REDIRECT_TO = "hearbe_recent_login_redirect_to"
CTX_RECENT_LOGIN_REDIRECT_TS = "hearbe_recent_login_redirect_ts"
CTX_RECENT_LOGIN_REDIRECT_REASON = "hearbe_recent_login_redirect_reason"
CTX_LOGIN_GUIDANCE_URL = "hearbe_login_guidance_url"
CTX_LOGIN_GUIDANCE_TS = "hearbe_login_guidance_ts"
LOGIN_GUIDANCE_COOLDOWN_SEC = 60.0


class HearbeSessionGate:
    def __init__(self, sender, session_manager) -> None:
        self._sender = sender
        self._session = session_manager
        self._tts = TTSGenerator()

    async def handle_main_page_update(self, session_id: str, url: str) -> bool:
        if not self._sender or not self._session:
            return False
        if get_page_type(url) != "main":
            return False
        if not _is_hearbe_site(url):
            return False
        if self._session.get_context(session_id, "token_recovery_in_flight"):
            logger.info("hearbe session gate main skip: token recovery in flight")
            return False
        if self._session.get_context(session_id, CTX_SESSION_CHECK_PENDING):
            logger.info("hearbe session gate main skip: CTX_SESSION_CHECK_PENDING is True")
            return True
        return await self._start_session_check(
            session_id,
            url,
            source="main_page",
            previous_url=None,
        )

    async def handle_login_page_update(
        self,
        session_id: str,
        url: str,
        previous_url: Optional[str] = None,
    ) -> bool:
        if not self._sender or not self._session:
            return False
        if get_page_type(url) != "login":
            return False
        if not _is_hearbe_site(url):
            return False
        if self._session.get_context(session_id, "token_recovery_in_flight"):
            logger.info("hearbe session gate login skip: token recovery in flight")
            return False
        if previous_url and get_page_type(previous_url) == "login":
            logger.info("hearbe session gate login skip: previous_url was also login")
            return False
        if self._session.get_context(session_id, CTX_SESSION_CHECK_PENDING):
            logger.info("hearbe session gate login skip: CTX_SESSION_CHECK_PENDING is True")
            return True

        # Check existing session before showing login UI.
        return await self._start_session_check(
            session_id,
            url,
            source="login_page",
            previous_url=previous_url,
        )

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]) -> bool:
        tool_name = data.get("tool_name")
        if tool_name != "get_user_session":
            return False
        if not self._sender or not self._session:
            return False
        if not self._session.get_context(session_id, CTX_SESSION_CHECK_PENDING):
            return False

        self._session.set_context(session_id, CTX_SESSION_CHECK_PENDING, None)
        result = data.get("result") or {}
        if not isinstance(result, dict):
            return False

        logged_in = bool(result.get("logged_in", False))
        user_type = (result.get("user_type") or result.get("userType") or "") or ""

        check_url = self._session.get_context(session_id, CTX_SESSION_CHECK_URL) or ""
        check_source = self._session.get_context(session_id, CTX_SESSION_CHECK_SOURCE) or ""
        check_previous_url = self._session.get_context(session_id, CTX_SESSION_CHECK_PREVIOUS_URL) or ""

        # Clear per-check metadata to avoid reuse across fast page bounces.
        self._session.set_context(session_id, CTX_SESSION_CHECK_URL, None)
        self._session.set_context(session_id, CTX_SESSION_CHECK_SOURCE, None)
        self._session.set_context(session_id, CTX_SESSION_CHECK_PREVIOUS_URL, None)

        if self._session.get_context(session_id, "token_recovery_in_flight"):
            logger.info(
                "hearbe session gate skip: session=%s token recovery in flight (url=%s)",
                session_id,
                check_url,
            )
            return False

        if not _is_hearbe_site(check_url):
            return False

        if logged_in:
            redirect_url = _resolve_mall_url(check_url, user_type=user_type)
            session = self._session.get_session(session_id) if self._session else None
            current_url = session.current_url if session else ""

            # If we're already on the target page (common during frontend redirect bounces),
            # avoid redundant navigation and confusing TTS.
            if current_url and redirect_url and current_url == redirect_url:
                logger.info(
                    "hearbe session found: session=%s user_type=%s already_on_redirect_url=%s source=%s - skip",
                    session_id,
                    user_type,
                    redirect_url,
                    check_source or "missing",
                )
                return False

            # Hearbe login-page entry is sometimes a frontend auth redirect (e.g. token check).
            # In that bounce case, avoid confusing "already logged in" TTS and redundant redirects.
            if check_source == "login_page":
                already_left_login = bool(
                    current_url and current_url != check_url and get_page_type(current_url) != "login"
                )
                if already_left_login:
                    logger.info(
                        "hearbe session found (bounce): session=%s user_type=%s current_url=%s prev_url=%s - skip",
                        session_id,
                        user_type,
                        current_url,
                        check_previous_url or "missing",
                    )
                    return False

            logger.info(
                "hearbe session found: session=%s user_type=%s redirect=%s",
                session_id,
                user_type,
                redirect_url,
            )
            await self._sender.send_tool_calls(
                session_id,
                [
                    MCPCommand(
                        tool_name="navigate_to_url",
                        arguments={"url": redirect_url},
                        description=f"redirect to {user_type or 'user'} mall",
                    )
                ],
            )
            # Avoid duplicate TTS: /mall page entry already announces guidance.
            if check_source != "login_page" and self._session:
                if get_page_type(redirect_url) == "mall":
                    self._session.set_context(session_id, CTX_RECENT_LOGIN_REDIRECT_TO, redirect_url)
                    self._session.set_context(session_id, CTX_RECENT_LOGIN_REDIRECT_TS, time.time())
                    self._session.set_context(session_id, CTX_RECENT_LOGIN_REDIRECT_REASON, "already_logged_in")
                else:
                    await self._sender.send_tts_response(
                        session_id,
                        "이미 로그인되어 있습니다. 이동을 진행합니다.",
                    )
            return True

        # Not logged in.
        page_type = get_page_type(check_url)
        if check_source == "main_page" and page_type == "main":
            # On Hearbe /main: stay and announce mode selection guidance.
            session = self._session.get_session(session_id) if self._session else None
            current_url = session.current_url if session else ""
            if current_url and get_page_type(current_url) != "main":
                logger.info(
                    "hearbe session gate (main) skip: session=%s current_url_changed=%s check_url=%s",
                    session_id,
                    current_url,
                    check_url,
                )
                return False

            if not self._is_tts_suppressed(session_id):
                await self._sender.send_tts_response(session_id, self._tts.build_hearbe_main_guidance())
            return True

        # On Hearbe login page, announce login/signup guidance once per entry.
        if check_source == "login_page" and page_type == "login":
            if not self._is_tts_suppressed(session_id) and self._should_send_login_guidance(session_id, check_url):
                await self._sender.send_tts_response(
                    session_id,
                    self._tts.build_hearbe_login_redirect(),
                )
            return True

        # Otherwise, do nothing (let the user log in manually).
        return False

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_SESSION_CHECK_PENDING, None)
        self._session.set_context(session_id, CTX_SESSION_CHECK_URL, None)
        self._session.set_context(session_id, CTX_SESSION_CHECK_SOURCE, None)
        self._session.set_context(session_id, CTX_SESSION_CHECK_PREVIOUS_URL, None)
        self._session.set_context(session_id, CTX_RECENT_LOGIN_REDIRECT_TO, None)
        self._session.set_context(session_id, CTX_RECENT_LOGIN_REDIRECT_TS, None)
        self._session.set_context(session_id, CTX_RECENT_LOGIN_REDIRECT_REASON, None)
        self._session.set_context(session_id, CTX_LOGIN_GUIDANCE_URL, None)
        self._session.set_context(session_id, CTX_LOGIN_GUIDANCE_TS, None)

    async def _start_session_check(
        self,
        session_id: str,
        url: str,
        source: str = "",
        previous_url: Optional[str] = None,
    ) -> bool:
        self._session.set_context(session_id, CTX_SESSION_CHECK_PENDING, True)
        self._session.set_context(session_id, CTX_SESSION_CHECK_URL, url)
        self._session.set_context(session_id, CTX_SESSION_CHECK_SOURCE, source or "")
        self._session.set_context(session_id, CTX_SESSION_CHECK_PREVIOUS_URL, previous_url or "")

        logger.info(
            "hearbe session check start: session=%s url=%s source=%s",
            session_id,
            url,
            source or "missing",
        )
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="get_user_session",
                    arguments={},
                    description="check existing hearbe user session",
                )
            ],
        )
        return True

    def _is_tts_suppressed(self, session_id: str) -> bool:
        if not self._session:
            return False
        until = self._session.get_context(session_id, "tts_suppress_until", 0)
        if until and time.time() < float(until):
            return True
        return False

    def _should_send_login_guidance(self, session_id: str, url: str) -> bool:
        if not self._session:
            return False
        last_url = self._session.get_context(session_id, CTX_LOGIN_GUIDANCE_URL) or ""
        last_ts = self._session.get_context(session_id, CTX_LOGIN_GUIDANCE_TS) or 0
        try:
            last_ts = float(last_ts)
        except (TypeError, ValueError):
            last_ts = 0.0
        if last_url == url and (time.time() - last_ts) < LOGIN_GUIDANCE_COOLDOWN_SEC:
            return False
        self._session.set_context(session_id, CTX_LOGIN_GUIDANCE_URL, url)
        self._session.set_context(session_id, CTX_LOGIN_GUIDANCE_TS, time.time())
        return True


def _is_hearbe_site(url: str) -> bool:
    if not url:
        return False
    site = get_current_site(url)
    return bool(site and site.site_id == "hearbe")


def _resolve_mall_url(current_url: str, user_type: str) -> str:
    site = get_current_site(current_url)
    urls = site.urls if site else {}
    utype = str(user_type or "").strip().upper()
    if utype == "BLIND":
        return urls.get("mall_a") or urls.get("mall_c") or urls.get("home") or current_url
    if utype in ("LOW_VISION", "LOWVISION", "B"):
        return urls.get("mall_b") or urls.get("mall_c") or urls.get("home") or current_url
    return urls.get("mall_c") or urls.get("mall_b") or urls.get("home") or current_url


__all__ = ["HearbeSessionGate"]
