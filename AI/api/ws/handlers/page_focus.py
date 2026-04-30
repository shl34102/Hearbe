# -*- coding: utf-8 -*-
"""
Page focus manager.

Problem:
- MCP can keep multiple tabs open (platform + shopping site). Each tab emits PAGE_UPDATE.
- If we treat every PAGE_UPDATE as the "current" page, session.current_url flips between tabs.
  This breaks:
  - LLM context (wrong site/page_type)
  - auto-extract timing (extract skipped or applied to wrong tab)
  - page-entry guidance TTS (repeated / out-of-context)

Approach:
- Maintain a per-session "primary" page_id and host (focus).
- Allow switching from platform(host endswith ssafy.io) -> external shopping site (e.g., coupang.com).
- Once focused on an external shopping site, ignore platform PAGE_UPDATE noise unless explicitly forced later.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CTX_PRIMARY_PAGE_ID = "primary_page_id"
CTX_PRIMARY_HOST = "primary_host"


def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _is_platform_host(host: str) -> bool:
    # Hearbe (platform) is served from ssafy.io domains.
    return bool(host) and host.endswith("ssafy.io")


def _is_coupang_host(host: str) -> bool:
    return bool(host) and host.endswith("coupang.com")


def _kind(host: str) -> str:
    if _is_platform_host(host):
        return "platform"
    if _is_coupang_host(host):
        return "coupang"
    return "other"


@dataclass
class FocusDecision:
    accept: bool
    switched: bool = False
    primary_page_id: Optional[int] = None
    primary_host: str = ""


class PageFocusManager:
    def __init__(self, session_manager):
        self._session = session_manager

    def decide(self, session_id: str, url: str, page_id: Optional[int], current_url: str) -> FocusDecision:
        """
        Decide whether to accept this PAGE_UPDATE as the session "current" page.

        Returns:
            FocusDecision(accept=...)
        """
        if not self._session or not session_id or not url:
            return FocusDecision(accept=True)

        # If we don't have a page_id, we can't safely focus-filter. Accept.
        if page_id is None:
            return FocusDecision(accept=True)

        incoming_host = _host(url)
        current_host = _host(current_url or "")
        incoming_kind = _kind(incoming_host)
        current_kind = _kind(current_host)

        primary_page_id = self._session.get_context(session_id, CTX_PRIMARY_PAGE_ID)
        primary_host = self._session.get_context(session_id, CTX_PRIMARY_HOST) or ""
        primary_kind = _kind(str(primary_host))

        if primary_page_id is None:
            # First page we see becomes the focus.
            self._session.set_context(session_id, CTX_PRIMARY_PAGE_ID, page_id)
            self._session.set_context(session_id, CTX_PRIMARY_HOST, incoming_host)
            return FocusDecision(
                accept=True,
                switched=True,
                primary_page_id=page_id,
                primary_host=incoming_host,
            )

        try:
            primary_page_id_int = int(primary_page_id)
        except Exception:
            primary_page_id_int = None

        # If a guided signup flow is active on the platform, keep focus pinned
        # to the primary page_id to prevent background tabs from clearing flow state.
        if (
            self._session.get_context(session_id, "hearbe_b_signup_flow_active")
            and primary_page_id_int is not None
            and page_id != primary_page_id_int
            and primary_kind == "platform"
            and incoming_kind == "platform"
        ):
            return FocusDecision(accept=False, primary_page_id=primary_page_id_int, primary_host=str(primary_host))

        if primary_page_id_int == page_id:
            return FocusDecision(accept=True, primary_page_id=page_id, primary_host=str(primary_host))

        # Switching rules:
        # 1) platform -> coupang/other external: allow switch (typical: mall card opens new tab).
        if primary_kind == "platform" and incoming_kind != "platform":
            self._session.set_context(session_id, CTX_PRIMARY_PAGE_ID, page_id)
            self._session.set_context(session_id, CTX_PRIMARY_HOST, incoming_host)
            logger.info(
                "Page focus switched: session=%s from=%s(%s) to=%s(%s) page_id=%s",
                session_id,
                primary_host,
                primary_kind,
                incoming_host,
                incoming_kind,
                page_id,
            )
            return FocusDecision(accept=True, switched=True, primary_page_id=page_id, primary_host=incoming_host)

        # 2) already external -> platform: ignore (prevents platform noise from overriding active shopping tab).
        if primary_kind != "platform" and incoming_kind == "platform":
            return FocusDecision(accept=False, primary_page_id=primary_page_id_int, primary_host=str(primary_host))

        # 3) same-kind external (e.g., coupang main -> search in another tab): allow switch.
        # This keeps focus stable within the active shopping site family.
        if incoming_kind == primary_kind:
            self._session.set_context(session_id, CTX_PRIMARY_PAGE_ID, page_id)
            self._session.set_context(session_id, CTX_PRIMARY_HOST, incoming_host)
            logger.info(
                "Page focus switched (same kind): session=%s kind=%s page_id=%s host=%s",
                session_id,
                incoming_kind,
                page_id,
                incoming_host,
            )
            return FocusDecision(accept=True, switched=True, primary_page_id=page_id, primary_host=incoming_host)

        # Default: accept (conservative), but update focus to the newest page_id.
        self._session.set_context(session_id, CTX_PRIMARY_PAGE_ID, page_id)
        self._session.set_context(session_id, CTX_PRIMARY_HOST, incoming_host)
        logger.info(
            "Page focus switched (default): session=%s from_kind=%s to_kind=%s page_id=%s host=%s",
            session_id,
            primary_kind,
            incoming_kind,
            page_id,
            incoming_host,
        )
        return FocusDecision(accept=True, switched=True, primary_page_id=page_id, primary_host=incoming_host)
