# -*- coding: utf-8 -*-
"""
Fast ACK generator for immediate user feedback before long operations.
"""

import os
from typing import Optional, Iterable

from core.interfaces import IntentType, MCPCommand


_DEFAULT_ACKS = {
    "generic": "\ud655\uc778\ud574\ubcf4\uaca0\uac8c\uc694.",
    "search": "\uac80\uc0c9\uc744 \uc2dc\uc791\ud560\uac8c\uc694.",
    "product": "\uc0c1\ud488\uc744 \ud655\uc778\ud558\uace0 \uc9c4\ud589\ud560\uac8c\uc694.",
    "cart": "\uc7a5\ubc14\uad6c\ub2c8 \uc791\uc5c5\uc744 \uc9c4\ud589\ud560\uac8c\uc694.",
    "checkout": "\uacb0\uc81c\ub97c \uc9c4\ud589\ud560\uac8c\uc694.",
    "login": "\ub85c\uadf8\uc778\uc744 \uc9c4\ud589\ud560\uac8c\uc694.",
}

_SKIP_TEXTS = {
    "\ub124", "\uc751", "\uc608", "\uadf8\ub798", "\ub9de\uc544", "\uadf8\ub7ec", "\uc544\ub2c8", "\uc544\ub2c8\uc694", "\uad1c\ucc2e", "\ucde8\uc18c", "\uadf8\ub9cc",
}

_ORDER_LIST_PHRASES = (
    "\uc8fc\ubb38 \ubaa9\ub85d",
    "\uc8fc\ubb38\ubaa9\ub85d",
    "\uc8fc\ubb38 \ub0b4\uc5ed",
    "\uc8fc\ubb38\ub0b4\uc5ed",
    "\uc8fc\ubb38 \uc870\ud68c",
    "\uc8fc\ubb38\uc870\ud68c",
    "\uc8fc\ubb38 \ub9ac\uc2a4\ud2b8",
    "\uc8fc\ubb38\ub9ac\uc2a4\ud2b8",
)

_NAVIGATION_TOOLS = {
    "goto",
    "wait_for_new_page",
}

_WAIT_TOOLS = {
    "wait",
    "wait_for_selector",
}

_MIN_WAIT_MS = int(os.getenv("FAST_ACK_MIN_WAIT_MS", "1000"))


def _has_navigation(commands: Iterable[MCPCommand]) -> bool:
    for cmd in commands or []:
        tool = (cmd.tool_name or "").strip()
        if tool in _NAVIGATION_TOOLS:
            return True
        if tool in _WAIT_TOOLS:
            args = cmd.arguments or {}
            if tool == "wait":
                if int(args.get("ms") or 0) >= _MIN_WAIT_MS:
                    return True
            if tool == "wait_for_selector":
                if int(args.get("timeout") or 0) >= 5000:
                    return True
    return False


class FastAckGenerator:
    def __init__(self, enabled: Optional[bool] = None):
        if enabled is None:
            enabled = os.getenv("FAST_ACK_ENABLED", "true").lower() in ("1", "true", "yes", "y")
        self._enabled = bool(enabled)

    def get_ack(
        self,
        user_text: str,
        page_type: Optional[str],
        intent: Optional[IntentType],
        commands: Optional[Iterable[MCPCommand]],
    ) -> Optional[str]:
        if not self._enabled:
            return None
        if not user_text:
            return None
        text = user_text.strip()
        if not text or text in _SKIP_TEXTS:
            return None
        if any(phrase in text for phrase in _ORDER_LIST_PHRASES):
            return None
        if intent in (IntentType.CONFIRM, IntentType.CANCEL):
            return None
        if not commands or not _has_navigation(commands):
            return None

        if intent == IntentType.SEARCH:
            return _DEFAULT_ACKS["search"]
        if intent == IntentType.ADD_TO_CART:
            return _DEFAULT_ACKS["cart"]
        if intent == IntentType.CHECKOUT:
            return _DEFAULT_ACKS["checkout"]
        if intent == IntentType.LOGIN:
            return _DEFAULT_ACKS["login"]

        if page_type and page_type in _DEFAULT_ACKS:
            return _DEFAULT_ACKS[page_type]
        return _DEFAULT_ACKS["generic"]


__all__ = ["FastAckGenerator"]
