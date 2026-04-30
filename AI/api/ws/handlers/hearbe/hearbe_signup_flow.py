# -*- coding: utf-8 -*-
"""
Hearbe signup flow helper.

Stores signup credentials and auto logs in after signup completion.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_current_site, get_page_type, get_selector


CTX_SIGNUP_LAST_ID = "hearbe_signup_last_id"
CTX_SIGNUP_LAST_PW = "hearbe_signup_last_pw"
CTX_SIGNUP_LAST_TS = "hearbe_signup_last_ts"
CTX_AUTOLOGIN_PENDING = "hearbe_signup_autologin_pending"
CTX_AUTOLOGIN_TS = "hearbe_signup_autologin_ts"

AUTOLOGIN_TTL_SEC = 300


class HearbeSignupFlowManager:
    def __init__(self, sender, session_manager, login_feedback=None):
        self._sender = sender
        self._session = session_manager
        self._login_feedback = login_feedback

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        session = self._session.get_session(session_id) if self._session else None
        if not session:
            return False

        current_url = session.current_url or ""
        if get_page_type(current_url) != "signup":
            return False
        site = get_current_site(current_url)
        if not site or getattr(site, "site_id", "") != "hearbe":
            return False

        normalized = _normalize_text(text)
        if not normalized:
            return False

        fields = _extract_signup_fields(normalized)
        if fields.get("username"):
            self._session.set_context(session_id, CTX_SIGNUP_LAST_ID, fields["username"])
            self._session.set_context(session_id, CTX_SIGNUP_LAST_TS, time.time())
        if fields.get("password"):
            self._session.set_context(session_id, CTX_SIGNUP_LAST_PW, fields["password"])
            self._session.set_context(session_id, CTX_SIGNUP_LAST_TS, time.time())

        if _is_submit_intent(normalized):
            self._session.set_context(session_id, CTX_AUTOLOGIN_PENDING, True)
            self._session.set_context(session_id, CTX_AUTOLOGIN_TS, time.time())

        return False

    async def handle_page_update(self, session_id: str, url: str, previous_url: Optional[str] = None) -> bool:
        if not self._sender or not self._session:
            return False
        if get_page_type(url) != "login":
            return False
        site = get_current_site(url)
        if not site or getattr(site, "site_id", "") != "hearbe":
            return False

        pending = self._session.get_context(session_id, CTX_AUTOLOGIN_PENDING)
        if not pending:
            return False
        if _is_expired(self._session.get_context(session_id, CTX_AUTOLOGIN_TS)):
            self._clear_pending(session_id)
            return False

        login_id = self._session.get_context(session_id, CTX_SIGNUP_LAST_ID)
        login_pw = self._session.get_context(session_id, CTX_SIGNUP_LAST_PW)
        if not login_id or not login_pw:
            self._clear_pending(session_id)
            return False

        id_selector = get_selector(url, "id_input") or get_selector(url, "email_input") or "input[type='text']"
        pw_selector = get_selector(url, "password_input") or "input[type='password']"
        login_selector = (
            get_selector(url, "login_button")
            or get_selector(url, "submit_button")
            or "button[type='submit']"
        )

        commands = [
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": id_selector, "state": "visible", "timeout": 8000},
                description="회원가입 후 로그인 아이디 입력칸 대기",
            ),
            MCPCommand(
                tool_name="fill",
                arguments={"selector": id_selector, "text": login_id},
                description="회원가입 후 로그인 아이디 입력",
            ),
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": pw_selector, "state": "visible", "timeout": 8000},
                description="회원가입 후 로그인 비밀번호 입력칸 대기",
            ),
            MCPCommand(
                tool_name="fill",
                arguments={"selector": pw_selector, "text": login_pw},
                description="회원가입 후 로그인 비밀번호 입력",
            ),
            MCPCommand(
                tool_name="click",
                arguments={"selector": login_selector},
                description="회원가입 후 로그인 버튼 클릭",
            ),
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 2000},
                description="회원가입 후 로그인 처리 대기",
            ),
        ]

        if self._login_feedback:
            try:
                self._login_feedback.mark_login_submit_pending(session_id, commands, url)
            except Exception:
                pass

        await self._sender.send_tool_calls(session_id, commands)
        self._clear_pending(session_id)
        return True

    def cleanup_session(self, session_id: str) -> None:
        self._clear_pending(session_id)
        if not self._session:
            return
        self._session.set_context(session_id, CTX_SIGNUP_LAST_ID, None)
        self._session.set_context(session_id, CTX_SIGNUP_LAST_PW, None)
        self._session.set_context(session_id, CTX_SIGNUP_LAST_TS, None)

    def _clear_pending(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_AUTOLOGIN_PENDING, None)
        self._session.set_context(session_id, CTX_AUTOLOGIN_TS, None)


def _is_expired(pending_ts: Optional[float]) -> bool:
    if not pending_ts:
        return True
    try:
        ts = float(pending_ts)
    except (TypeError, ValueError):
        return True
    return (time.time() - ts) > AUTOLOGIN_TTL_SEC


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _extract_signup_fields(text: str) -> dict:
    fields = {}
    username = _extract_labeled_alnum(text, ("아이디", "id"), 4, 20)
    if username:
        fields["username"] = username

    password = _extract_labeled_alnum(
        text,
        ("비밀번호", "비번", "패스워드", "password", "pw"),
        4,
        32,
    )
    if password:
        fields["password"] = password

    return fields


def _extract_labeled_alnum(text: str, labels: tuple[str, ...], min_len: int, max_len: int) -> Optional[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_pattern})\s*(?:[:：]|은|는|이|가)?\s*([A-Za-z0-9\\s]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    value = re.sub(r"\\s+", "", match.group(1))
    return _sanitize_alnum(value, min_len, max_len)


def _sanitize_alnum(value: str, min_len: int, max_len: int) -> Optional[str]:
    if not value:
        return None
    value = re.sub(r"[^A-Za-z0-9]", "", value)
    if len(value) < min_len or len(value) > max_len:
        return None
    return value


def _is_submit_intent(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "회원가입" in text or "회원 가입" in text:
        return True
    submit_tokens = (
        "가입해",
        "가입해줘",
        "가입해주세요",
        "가입할게",
        "가입 진행",
        "가입 신청",
        "가입 완료",
        "회원등록",
        "회원 등록",
    )
    if any(token in text for token in submit_tokens):
        return True
    if "signup" in lowered or "sign up" in lowered:
        return True
    return False


__all__ = ["HearbeSignupFlowManager"]
