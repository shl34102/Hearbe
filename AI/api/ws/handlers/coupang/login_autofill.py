# -*- coding: utf-8 -*-
"""
Coupang login autofill helper.

If the user asks to log in while on the Coupang login page, check whether
email/password fields are already filled (e.g., by browser autofill).
If filled, click the login button immediately. Otherwise, fall back to
the usual guidance prompt.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

from core.interfaces import MCPCommand
from services.llm.generators.tts_generator import TTSGenerator
from services.llm.sites.site_manager import get_page_type, get_selector

logger = logging.getLogger(__name__)


CTX_EMAIL_ARGS = "login_autofill_email_args"
CTX_PASS_ARGS = "login_autofill_pass_args"
CTX_EMAIL_FILLED = "login_autofill_email_filled"
CTX_PASS_FILLED = "login_autofill_pass_filled"
CTX_PENDING = "login_autofill_pending"
CTX_ATTEMPT = "login_autofill_attempt"
CTX_LAST_URL = "login_autofill_last_url"
CTX_AUTOFILL_USED = "login_autofill_used"
CTX_FINALIZED = "login_autofill_finalized"
CTX_GUIDANCE_PENDING = "login_page_guidance_pending"
CTX_GUIDANCE_SENT = "login_page_guidance_sent"
CTX_GUIDANCE_PAGE = "login_page_guidance_page"
CTX_LOGOUT_SUPPRESS_UNTIL = "logout_guidance_suppress_until"

MAX_ATTEMPTS = 2
FOCUS_WAIT_MS = 300
RETRY_DELAY_MS = 1500


class LoginAutofillManager:
    """Detects Coupang login autofill and triggers submit."""

    def __init__(self, sender, session_manager, login_feedback=None):
        self._sender = sender
        self._session = session_manager
        self._login_feedback = login_feedback
        self._tts = TTSGenerator()

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        session = self._session.get_session(session_id) if self._session else None
        if not session:
            return False

        current_url = session.current_url or ""
        if get_page_type(current_url) != "login":
            return False
        if not _is_coupang_login_url(current_url):
            logger.info("login_autofill skip: not coupang login url (text)")
            return False

        if not _is_login_intent(text):
            return False

        # If we're already submitting login, ignore repeated "login" intents.
        if self._session.get_context(session_id, "login_submit_pending"):
            logger.info("login_autofill skip: login_submit_pending is True (coupang)")
            return True

        if self._session.get_context(session_id, CTX_PENDING):
            return True

        return await self._start_probe(session_id, current_url, source="text")

    async def handle_page_update(self, session_id: str, url: str, previous_url: Optional[str] = None) -> bool:
        page_type = get_page_type(url)
        logger.info(
            "login_autofill handle_page_update: session=%s url=%s page_type=%s previous_url=%s",
            session_id,
            url,
            page_type,
            previous_url,
        )
        if page_type != "login":
            logger.info("login_autofill skip: page_type is not login")
            return False
        if not _is_coupang_login_url(url):
            logger.info("login_autofill skip: not coupang login url")
            return False

        if self._session.get_context(session_id, "login_submit_pending"):
            logger.info("login_autofill skip: login_submit_pending is True (coupang page)")
            return True
        if previous_url and get_page_type(previous_url) == "login":
            logger.info("login_autofill skip: previous_url was also login (coupang)")
            return False
        if self._session.get_context(session_id, CTX_PENDING):
            logger.info("login_autofill skip: CTX_PENDING is True (coupang)")
            return True

        last_url = self._session.get_context(session_id, CTX_LAST_URL)
        if last_url == url:
            logger.info("login_autofill skip: same as last_url (coupang)")
            return False

        return await self._start_probe(session_id, url, source="page")

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]) -> bool:
        if data.get("tool_name") != "get_attribute_list":
            return False

        args = data.get("arguments") or {}
        result = data.get("result") or {}

        email_args = self._session.get_context(session_id, CTX_EMAIL_ARGS)
        pass_args = self._session.get_context(session_id, CTX_PASS_ARGS)
        if not email_args and not pass_args:
            return False

        if _args_match(email_args, args):
            filled = _has_non_empty_values(result)
            self._session.set_context(session_id, CTX_EMAIL_FILLED, filled)
            logger.info("login autofill email result: session=%s filled=%s", session_id, filled)
            return await self._maybe_finalize(session_id)

        if _args_match(pass_args, args):
            filled = _has_non_empty_values(result)
            self._session.set_context(session_id, CTX_PASS_FILLED, filled)
            logger.info("login autofill password result: session=%s filled=%s", session_id, filled)
            return await self._maybe_finalize(session_id)

        return False

    def cleanup_session(self, session_id: str):
        if not self._session:
            return
        self._session.set_context(session_id, CTX_EMAIL_ARGS, None)
        self._session.set_context(session_id, CTX_PASS_ARGS, None)
        self._session.set_context(session_id, CTX_EMAIL_FILLED, None)
        self._session.set_context(session_id, CTX_PASS_FILLED, None)
        self._session.set_context(session_id, CTX_PENDING, None)
        self._session.set_context(session_id, CTX_ATTEMPT, None)
        self._session.set_context(session_id, CTX_LAST_URL, None)
        self._session.set_context(session_id, CTX_AUTOFILL_USED, None)
        self._session.set_context(session_id, CTX_FINALIZED, None)

    async def _maybe_finalize(self, session_id: str) -> bool:
        if self._session.get_context(session_id, CTX_FINALIZED):
            return True
        email_filled = self._session.get_context(session_id, CTX_EMAIL_FILLED)
        pass_filled = self._session.get_context(session_id, CTX_PASS_FILLED)
        if email_filled is None or pass_filled is None:
            return True

        self._session.set_context(session_id, CTX_PENDING, False)

        session = self._session.get_session(session_id) if self._session else None
        current_url = session.current_url if session else ""

        if email_filled or pass_filled:
            logger.info(
                "login autofill success: session=%s email_filled=%s pass_filled=%s",
                session_id,
                email_filled,
                pass_filled,
            )
            self._session.set_context(session_id, CTX_AUTOFILL_USED, True)
            self._session.set_context(session_id, CTX_FINALIZED, True)
            await self._send_login_click(session_id, current_url)
            return True

        attempt = self._session.get_context(session_id, CTX_ATTEMPT) or 1
        if attempt < MAX_ATTEMPTS:
            logger.info(
                "login autofill retry: session=%s attempt=%s/%s",
                session_id,
                attempt + 1,
                MAX_ATTEMPTS,
            )
            self._session.set_context(session_id, CTX_ATTEMPT, attempt + 1)
            self._session.set_context(session_id, CTX_PENDING, True)
            # Reset for the next attempt so we don't accidentally finalize with stale values.
            self._session.set_context(session_id, CTX_EMAIL_FILLED, None)
            self._session.set_context(session_id, CTX_PASS_FILLED, None)
            email_args = self._session.get_context(session_id, CTX_EMAIL_ARGS)
            pass_args = self._session.get_context(session_id, CTX_PASS_ARGS)
            if email_args and pass_args:
                await self._sender.send_tool_calls(
                    session_id,
                    [
                        MCPCommand(
                            tool_name="wait",
                            arguments={"ms": RETRY_DELAY_MS},
                            description="wait for login autofill",
                        ),
                        MCPCommand(
                            tool_name="get_attribute_list",
                            arguments=email_args,
                            description="check login email autofill (retry)",
                        ),
                        MCPCommand(
                            tool_name="get_attribute_list",
                            arguments=pass_args,
                            description="check login password autofill (retry)",
                        ),
                    ],
                )
                return True

        # Autofill not detected; fall back to normal guidance.
        logger.info(
            "login autofill failed: session=%s email_filled=%s pass_filled=%s",
            session_id,
            email_filled,
            pass_filled,
        )
        self._session.set_context(session_id, CTX_FINALIZED, True)
        await self._send_login_guidance_if_needed(session_id, current_url)
        return True

    async def _send_login_guidance_if_needed(self, session_id: str, current_url: str) -> None:
        if not self._session or not self._sender:
            return
        until = self._session.get_context(session_id, CTX_LOGOUT_SUPPRESS_UNTIL, 0)
        if until:
            try:
                if time.time() < float(until):
                    return
            except Exception:
                pass
        page_key = current_url or ""
        if self._session.get_context(session_id, CTX_GUIDANCE_SENT) == page_key:
            return
        self._session.set_context(session_id, CTX_GUIDANCE_PENDING, None)
        self._session.set_context(session_id, CTX_GUIDANCE_PAGE, page_key)
        self._session.set_context(session_id, CTX_GUIDANCE_SENT, page_key)
        await self._sender.send_tts_response(session_id, self._tts.build_login_guidance())

    async def _start_probe(self, session_id: str, current_url: str, source: str) -> bool:
        if not _is_coupang_login_url(current_url):
            logger.info("login_autofill probe skip: not coupang login url")
            return False

        email_selector = get_selector(current_url, "email_input") or "#login-email-input"
        password_selector = get_selector(current_url, "password_input") or "#login-password-input"

        email_args = {"selector": email_selector, "attribute": "value"}
        pass_args = {"selector": password_selector, "attribute": "value"}
        self._session.set_context(session_id, CTX_EMAIL_ARGS, email_args)
        self._session.set_context(session_id, CTX_PASS_ARGS, pass_args)
        self._session.set_context(session_id, CTX_EMAIL_FILLED, None)
        self._session.set_context(session_id, CTX_PASS_FILLED, None)
        self._session.set_context(session_id, CTX_FINALIZED, None)
        self._session.set_context(session_id, CTX_ATTEMPT, 1)
        self._session.set_context(session_id, CTX_PENDING, True)
        self._session.set_context(session_id, CTX_LAST_URL, current_url)

        logger.info(
            "login autofill probe start: session=%s url=%s source=%s email_selector=%s pass_selector=%s",
            session_id,
            current_url,
            source,
            email_selector,
            password_selector,
        )
        await self._send_probe(
            session_id,
            email_selector,
            password_selector,
            email_args,
            pass_args,
            with_focus=True,
        )
        return True

    async def _send_login_click(self, session_id: str, current_url: str):
        login_selector = (
            get_selector(current_url, "login_button")
            or get_selector(current_url, "submit_button")
            or "button[type='submit']"
        )
        commands = [
            MCPCommand(
                tool_name="click",
                arguments={"selector": login_selector},
                description="login submit",
            ),
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 2000},
                description="wait for login",
            ),
        ]
        if self._login_feedback:
            self._login_feedback.mark_login_submit_pending(session_id, commands, current_url or "")
        await self._sender.send_tool_calls(session_id, commands)

    async def _send_probe(
        self,
        session_id: str,
        email_selector: str,
        password_selector: str,
        email_args: Dict[str, Any],
        pass_args: Dict[str, Any],
        with_focus: bool = False,
    ):
        commands = []
        if with_focus:
            commands.extend(
                [
                    MCPCommand(
                        tool_name="click",
                        arguments={"selector": email_selector},
                        description="focus login email input",
                    ),
                    MCPCommand(
                        tool_name="click",
                        arguments={"selector": password_selector},
                        description="focus login password input",
                    ),
                    MCPCommand(
                        tool_name="wait",
                        arguments={"ms": FOCUS_WAIT_MS},
                        description="wait for autofill after focus",
                    ),
                ]
            )
        commands.extend(
            [
                MCPCommand(
                    tool_name="get_attribute_list",
                    arguments=email_args,
                    description="check login email autofill",
                ),
                MCPCommand(
                    tool_name="get_attribute_list",
                    arguments=pass_args,
                    description="check login password autofill",
                ),
            ]
        )
        await self._sender.send_tool_calls(session_id, commands)


def _has_non_empty_values(result: Dict[str, Any]) -> bool:
    values = result.get("values") if isinstance(result, dict) else None
    if not values:
        return False
    return any(v and v.strip() for v in values)


def _is_login_intent(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "로그인" not in text and "login" not in lowered:
        return False
    if any(k in text for k in ("이메일", "인증", "문자")):
        return False
    if "otp" in lowered or "code" in lowered:
        return False
    # Avoid hijacking pure OTP/phone digit inputs.
    digits = re.sub(r"\\D", "", text)
    if 4 <= len(digits) <= 8 and "로그인" not in text:
        return False
    return True


def _args_match(expected: Optional[Dict[str, Any]], actual: Dict[str, Any]) -> bool:
    if not expected:
        return False
    for key, value in expected.items():
        if actual.get(key) != value:
            return False
    return True




def _is_coupang_login_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return "login.coupang.com" in lowered and "/login/login.pang" in lowered


__all__ = ["LoginAutofillManager"]
