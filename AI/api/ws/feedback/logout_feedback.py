# -*- coding: utf-8 -*-
"""
Logout feedback manager.

Marks a short-lived suppression window to avoid extra guidance
after a logout click redirects to the login page.
"""

import re
import time


CTX_LOGOUT_SUPPRESS_UNTIL = "logout_guidance_suppress_until"
CTX_LOGOUT_CONFIRM_PENDING = "logout_confirm_pending"
SUPPRESS_WINDOW_SEC = 8.0
CONFIRM_PENDING_TTL_SEC = 20.0


class LogoutFeedbackManager:
    """Track logout clicks to suppress follow-up login guidance briefly."""

    def __init__(self, session_manager):
        self._session = session_manager

    def mark_logout_pending(self, session_id: str, commands, current_url: str):
        if not self._session or not commands:
            return
        if not _has_logout_click(commands):
            return
        self._session.set_context(
            session_id,
            CTX_LOGOUT_SUPPRESS_UNTIL,
            time.time() + SUPPRESS_WINDOW_SEC,
        )
        if _should_prompt_logout_confirm(current_url):
            self._session.set_context(
                session_id,
                CTX_LOGOUT_CONFIRM_PENDING,
                time.time(),
            )

    def clear_pending(self, session_id: str):
        if self._session:
            self._session.set_context(session_id, CTX_LOGOUT_SUPPRESS_UNTIL, None)
            self._session.set_context(session_id, CTX_LOGOUT_CONFIRM_PENDING, None)


def _has_logout_click(commands) -> bool:
    for cmd in commands:
        try:
            tool = getattr(cmd, "tool_name", "") or ""
            args = getattr(cmd, "arguments", None) or {}
            if tool in ("click", "click_element"):
                selector = (args.get("selector") or "").lower()
                if "logout" in selector or "\ub85c\uadf8\uc544\uc6c3" in selector:
                    return True
            if tool == "click_text":
                text = (args.get("text") or "").strip()
                if text == "\ub85c\uadf8\uc544\uc6c3":
                    return True
        except Exception:
            continue
    return False


def _should_prompt_logout_confirm(current_url: str) -> bool:
    if not current_url:
        return False
    lowered = current_url.lower()
    return bool(re.search(r"/c/mall(?:\\b|/|\\?)", lowered))


__all__ = [
    "CTX_LOGOUT_CONFIRM_PENDING",
    "CONFIRM_PENDING_TTL_SEC",
    "LogoutFeedbackManager",
]
