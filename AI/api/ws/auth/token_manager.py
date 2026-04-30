# -*- coding: utf-8 -*-
"""
Centralized token manager for AI server.

Responsibilities:
- Store access/refresh tokens in session context
- Refresh access token via backend refresh API
- Recover tokens by navigating to main page and calling get_user_session
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from core.interfaces import MCPCommand

logger = logging.getLogger(__name__)

CTX_ACCESS_TOKEN = "access_token"
CTX_REFRESH_TOKEN = "refresh_token"
CTX_TOKEN_REFRESHING = "token_refreshing"
CTX_TOKEN_LAST_REFRESH_TS = "token_last_refresh_ts"
CTX_TOKEN_RECOVERY_IN_FLIGHT = "token_recovery_in_flight"
CTX_TOKEN_LAST_RECOVERY_TS = "token_last_recovery_ts"
CTX_TOKEN_LAST_SOURCE = "token_last_source"

TOKEN_REFRESH_COOLDOWN_SEC = 5.0
TOKEN_RECOVERY_COOLDOWN_SEC = 8.0


class TokenManager:
    def __init__(self, sender, session_manager) -> None:
        self._sender = sender
        self._session = session_manager
        self._backend_base = os.getenv("BACKEND_BASE_URL", "https://i14d108.p.ssafy.io").rstrip("/")
        self._main_url = os.getenv("MAIN_PAGE_URL", "https://i14d108.p.ssafy.io/main")
        self._general_url = os.getenv("GENERAL_URL", "").strip()
        self._blind_url = os.getenv("BLIND_URL", "").strip()
        self._low_vision_url = os.getenv("LOW_VISION_URL", "").strip()

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_TOKEN_REFRESHING, None)
        self._session.set_context(session_id, CTX_TOKEN_LAST_REFRESH_TS, None)
        self._session.set_context(session_id, CTX_TOKEN_RECOVERY_IN_FLIGHT, None)
        self._session.set_context(session_id, CTX_TOKEN_LAST_RECOVERY_TS, None)
        self._session.set_context(session_id, CTX_TOKEN_LAST_SOURCE, None)

    def get_access_token(self, session_id: str) -> str:
        return self._get_token_from_context(session_id, is_refresh=False)

    def get_refresh_token(self, session_id: str) -> str:
        return self._get_token_from_context(session_id, is_refresh=True)

    def invalidate_access_token(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_ACCESS_TOKEN, None)
        logger.info("Token invalidated: session=%s access_token=cleared", session_id)

    async def handle_user_session(self, session_id: str, data: Dict[str, Any]) -> Tuple[str, str]:
        result = data.get("result") or {}
        if not isinstance(result, dict):
            logger.warning(
                "get_user_session result invalid: session=%s type=%s",
                session_id,
                type(result),
            )
            return "", ""
        access_token = result.get("access_token") or result.get("accessToken") or ""
        refresh_token = result.get("refresh_token") or result.get("refreshToken") or ""
        user_type = result.get("user_type") or result.get("userType") or ""
        if user_type and self._session:
            self._session.set_context(session_id, "user_type", str(user_type))
        self.update_tokens(
            session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            source="get_user_session",
        )
        if self._session:
            self._session.set_context(session_id, CTX_TOKEN_RECOVERY_IN_FLIGHT, None)
        return access_token, refresh_token

    def update_tokens(
        self,
        session_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        source: str = "",
    ) -> None:
        if not self._session:
            return
        access_token = _normalize_token(access_token)
        refresh_token = _normalize_token(refresh_token)
        if access_token:
            self._session.set_context(session_id, CTX_ACCESS_TOKEN, access_token)
            self._session.set_context(session_id, "token_access_ts", time.time())
        if refresh_token:
            self._session.set_context(session_id, CTX_REFRESH_TOKEN, refresh_token)
            self._session.set_context(session_id, "token_refresh_ts", time.time())
        if access_token or refresh_token:
            if source:
                self._session.set_context(session_id, CTX_TOKEN_LAST_SOURCE, source)
            logger.info(
                "Token updated: session=%s access_token=%s refresh_token=%s source=%s",
                session_id,
                _format_token(access_token) if access_token else "missing",
                _format_token(refresh_token) if refresh_token else "missing",
                source or "unknown",
            )

    async def ensure_access_token(
        self,
        session_id: str,
        return_url: Optional[str] = None,
        reason: str = "",
    ) -> Optional[str]:
        token = self.get_access_token(session_id)
        if token:
            return token
        refresh_token = self.get_refresh_token(session_id)
        if refresh_token:
            refreshed = await self._refresh_access_token(session_id, refresh_token, reason=reason)
            if refreshed:
                return self.get_access_token(session_id)
        await self._request_token_recovery(session_id, return_url=return_url, reason=reason)
        return None

    async def handle_auth_failure(
        self,
        session_id: str,
        status_code: int,
        return_url: Optional[str] = None,
        reason: str = "",
    ) -> Optional[str]:
        if status_code not in (401, 403):
            return None
        self.invalidate_access_token(session_id)
        return await self.ensure_access_token(session_id, return_url=return_url, reason=reason)

    async def _refresh_access_token(self, session_id: str, refresh_token: str, reason: str = "") -> bool:
        if not refresh_token:
            return False
        if not self._session:
            return False
        now = time.time()
        last_ts = self._session.get_context(session_id, CTX_TOKEN_LAST_REFRESH_TS, 0) or 0
        refreshing = bool(self._session.get_context(session_id, CTX_TOKEN_REFRESHING))
        if refreshing and now - last_ts < TOKEN_REFRESH_COOLDOWN_SEC:
            logger.info("Token refresh skipped (cooldown): session=%s", session_id)
            return False
        self._session.set_context(session_id, CTX_TOKEN_REFRESHING, True)
        self._session.set_context(session_id, CTX_TOKEN_LAST_REFRESH_TS, now)
        refresh_url = f"{self._backend_base}/api/auth/refresh"
        payload = {"refreshToken": refresh_token}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(refresh_url, json=payload)
            if response.status_code != 200:
                logger.warning(
                    "Token refresh failed: session=%s status=%s reason=%s",
                    session_id,
                    response.status_code,
                    reason or "unknown",
                )
                return False
            data = response.json() if response.content else {}
            token_payload = data.get("data") if isinstance(data, dict) and "data" in data else data
            if not isinstance(token_payload, dict):
                return False
            new_access = token_payload.get("accessToken") or token_payload.get("access_token")
            new_refresh = token_payload.get("refreshToken") or token_payload.get("refresh_token")
            self.update_tokens(
                session_id,
                access_token=new_access,
                refresh_token=new_refresh,
                source="refresh_api",
            )
            return bool(new_access)
        except Exception as exc:
            logger.warning("Token refresh error: session=%s error=%s", session_id, exc)
            return False
        finally:
            if self._session:
                self._session.set_context(session_id, CTX_TOKEN_REFRESHING, False)

    async def _request_token_recovery(
        self,
        session_id: str,
        return_url: Optional[str] = None,
        reason: str = "",
    ) -> None:
        if not self._sender or not self._session:
            return
        now = time.time()
        last_ts = self._session.get_context(session_id, CTX_TOKEN_LAST_RECOVERY_TS, 0) or 0
        inflight = bool(self._session.get_context(session_id, CTX_TOKEN_RECOVERY_IN_FLIGHT))
        if inflight and now - last_ts < TOKEN_RECOVERY_COOLDOWN_SEC:
            logger.info("Token recovery skipped (cooldown): session=%s", session_id)
            return
        self._session.set_context(session_id, CTX_TOKEN_RECOVERY_IN_FLIGHT, True)
        self._session.set_context(session_id, CTX_TOKEN_LAST_RECOVERY_TS, now)

        if not return_url and self._session:
            session = self._session.get_session(session_id)
            return_url = session.current_url if session else None

        recovery_url = self._resolve_recovery_url(session_id)
        commands = [
            MCPCommand(
                tool_name="navigate_to_url",
                arguments={"url": recovery_url},
                description="refresh access token on user page",
            ),
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 1200},
                description="wait for token page to load",
            ),
            MCPCommand(
                tool_name="get_user_session",
                arguments={},
                description="get user session from localStorage",
            ),
        ]
        if return_url and return_url != recovery_url:
            commands.extend(
                [
                    MCPCommand(
                        tool_name="navigate_to_url",
                        arguments={"url": return_url},
                        description="return to previous page",
                    ),
                    MCPCommand(
                        tool_name="wait",
                        arguments={"ms": 800},
                        description="wait for page to settle",
                    ),
                ]
            )
        await self._sender.send_tool_calls(session_id, commands)
        logger.info(
            "Token recovery requested: session=%s recovery_url=%s return_url=%s reason=%s",
            session_id,
            recovery_url,
            return_url or "missing",
            reason or "unknown",
        )

    def _get_token_from_context(self, session_id: str, is_refresh: bool) -> str:
        if not self._session:
            return ""
        keys = (
            ["refresh_token", "refreshToken"]
            if is_refresh
            else [
                "access_token",
                "accessToken",
                "jwt_token",
                "api_access_token",
                "auth_token",
                "token",
            ]
        )
        for key in keys:
            value = self._session.get_context(session_id, key)
            token = _normalize_token(value)
            if token:
                return token
        return ""

    def _resolve_recovery_url(self, session_id: str) -> str:
        if not self._session:
            return self._main_url
        user_type_raw = self._session.get_context(session_id, "user_type") or self._session.get_context(
            session_id, "userType"
        )
        user_type = str(user_type_raw or "").strip().upper()
        if user_type == "BLIND" and self._blind_url:
            return self._blind_url
        if user_type in ("GENERAL", "NORMAL") and self._general_url:
            return self._general_url
        if user_type in ("LOW_VISION", "LOWVISION", "B") and self._low_vision_url:
            return self._low_vision_url
        # Fallback to general URL first, then legacy MAIN_PAGE_URL.
        if self._general_url:
            return self._general_url
        return self._main_url


def _normalize_token(token: Optional[str]) -> str:
    if not token:
        return ""
    token = str(token).strip()
    if not token:
        return ""
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _format_token(token: Optional[str]) -> str:
    if not token:
        return ""
    if os.getenv("LOG_TOKEN_FULL", "").strip() == "1":
        return token
    # Default: show prefix/suffix only to reduce leakage.
    if len(token) <= 12:
        return token
    return f"{token[:6]}...{token[-6:]}"
