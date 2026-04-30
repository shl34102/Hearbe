# -*- coding: utf-8 -*-
"""
Hearbe C mall logout confirmation handler.

When logout opens a SweetAlert2 confirm modal, prompt the user and
handle yes/no responses to click confirm/cancel.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_selector
from ..feedback.logout_feedback import CTX_LOGOUT_CONFIRM_PENDING, CONFIRM_PENDING_TTL_SEC


class LogoutConfirmManager:
    def __init__(self, sender, session_manager, command_pipeline):
        self._sender = sender
        self._session = session_manager
        self._command_pipeline = command_pipeline

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        session = self._session.get_session(session_id) if self._session else None
        if not session:
            return False
        pending_ts = self._session.get_context(session_id, CTX_LOGOUT_CONFIRM_PENDING)
        if not pending_ts:
            return False
        if not _is_hearbe_c_mall_url(session.current_url or ""):
            self.clear_pending(session_id)
            return False
        if _is_expired(pending_ts):
            self.clear_pending(session_id)
            return False

        decision = _classify_response(text)
        if decision is None:
            await self._sender.send_tts_response(
                session_id,
                "로그아웃 하시겠습니까? 네 또는 아니오로 말씀해 주세요.",
            )
            return True

        current_url = session.current_url or ""
        if decision:
            selector = get_selector(current_url, "logout_confirm") or "button.swal2-confirm"
            response_text = "로그아웃 되었습니다."
            description = "confirm logout"
        else:
            selector = get_selector(current_url, "logout_cancel") or "button.swal2-cancel"
            response_text = "취소했습니다."
            description = "cancel logout"

        commands = [
            MCPCommand(
                tool_name="click",
                arguments={"selector": selector},
                description=description,
            )
        ]
        commands = self._command_pipeline.prepare_commands(
            session_id,
            commands,
            current_url,
            allow_extract=False,
        )
        await self._command_pipeline.dispatch(
            session_id,
            commands,
            response_text,
            current_url,
            lambda: False,
        )
        self.clear_pending(session_id)
        return True

    def clear_pending(self, session_id: str) -> None:
        if self._session:
            self._session.set_context(session_id, CTX_LOGOUT_CONFIRM_PENDING, None)

    def cleanup_session(self, session_id: str) -> None:
        self.clear_pending(session_id)


def _is_expired(pending_ts: Optional[float]) -> bool:
    if not pending_ts:
        return True
    try:
        ts = float(pending_ts)
    except (TypeError, ValueError):
        return True
    return (time.time() - ts) > CONFIRM_PENDING_TTL_SEC


def _is_hearbe_c_mall_url(current_url: str) -> bool:
    if not current_url:
        return False
    lowered = current_url.lower()
    return bool(re.search(r"/c/mall(?:\\b|/|\\?)", lowered))


_POSITIVE_TOKENS = (
    "네",
    "예",
    "응",
    "어",
    "그래",
    "그래요",
    "맞아",
    "맞아요",
    "확인",
    "진행",
    "해줘",
    "해주세요",
    "해",
    "로그아웃",
    "yes",
    "yeah",
    "yep",
    "ok",
    "okay",
)

_NEGATIVE_TOKENS = (
    "아니",
    "아니요",
    "아냐",
    "아뇨",
    "취소",
    "안해",
    "하지마",
    "그만",
    "됐어",
    "멈춰",
    "no",
    "nope",
)


def _classify_response(text: str) -> Optional[bool]:
    compact = _normalize(text)
    if not compact:
        return None
    if _contains_any(compact, _NEGATIVE_TOKENS):
        return False
    if _contains_any(compact, _POSITIVE_TOKENS):
        return True
    return None


def _normalize(text: str) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", "", text.strip().lower())
    return compact


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


__all__ = ["LogoutConfirmManager"]
