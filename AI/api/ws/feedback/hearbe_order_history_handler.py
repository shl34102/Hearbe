# -*- coding: utf-8 -*-
"""
Hearbe order history handler.

Why:
- Hearbe order history lives on our own site (i14d108...), not Coupang.
- LLM fallback may incorrectly call Coupang extractors (extract_order_list) on Hearbe pages.
- We want a deterministic, token-aware way to fetch and read order history.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from api.order.order_client import OrderClient

from ..auth.token_manager import TokenManager

logger = logging.getLogger(__name__)


CTX_HEARBE_ORDER_HISTORY_LAST_URL = "hearbe_order_history_last_url"
CTX_HEARBE_ORDER_HISTORY_DATA = "hearbe_order_history_data"
CTX_HEARBE_ORDER_HISTORY_RECOMMENDED = "hearbe_order_history_recommended"
CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING = "hearbe_order_history_prompt_pending"
CTX_HEARBE_ORDER_HISTORY_FETCHING = "hearbe_order_history_fetching"
CTX_HEARBE_ORDER_HISTORY_FETCHED_AT = "hearbe_order_history_fetched_at"

# Avoid spamming the API on rapid redirects or repeated page-update events.
FETCH_COOLDOWN_SEC = 5.0

_ORDER_HISTORY_URL_RE = re.compile(r"^https?://i14d108\.p\.ssafy\.io/[ABC]/order-history(?:[/?#].*)?$")


def is_hearbe_order_history_url(url: str) -> bool:
    return bool(url and _ORDER_HISTORY_URL_RE.match(url))


class HearbeOrderHistoryHandler:
    def __init__(
        self,
        sender,
        session_manager,
        token_manager: Optional[TokenManager] = None,
    ) -> None:
        self._sender = sender
        self._session = session_manager
        self._tokens = token_manager
        self._backend_url = os.getenv("BACKEND_BASE_URL", "https://i14d108.p.ssafy.io").rstrip("/")

    async def handle_page_update(self, session_id: str, current_url: str) -> bool:
        """
        When arriving on Hearbe order-history page, fetch orders and ask whether to read them.
        """
        if not self._sender or not self._session:
            return False
        if not is_hearbe_order_history_url(current_url):
            return False

        # Debounce repeated page updates for the same URL.
        last_url = self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_LAST_URL)
        if last_url == current_url and self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_DATA):
            return False
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_LAST_URL, current_url)

        # Cooldown to avoid repeated API calls during redirect loops (/member-info -> /login -> /mall etc).
        now = time.time()
        fetched_at = self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHED_AT, 0) or 0
        fetching = bool(self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHING))
        if fetching:
            return True
        if fetched_at and now - float(fetched_at) < FETCH_COOLDOWN_SEC:
            # Still set prompt_pending so follow-up "읽어줘" can be answered from cached data if present.
            if self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_DATA):
                if not self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING):
                    self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING, True)
            return True

        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHING, True)
        try:
            orders = await self._fetch_orders(session_id, return_url=current_url)
            if orders is None:
                return True
            self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_DATA, orders)
            self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHED_AT, time.time())

            # Ask once per arrival.
            prompt_pending = bool(self._session.get_context(session_id, CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING))
            if not prompt_pending:
                self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING, True)
                await self._sender.send_tts_response(
                    session_id,
                    "주문 내역 페이지로 이동이 완료되었습니다. 주문 내역을 읽어드릴까요?",
                )
            return True
        finally:
            self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHING, False)

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_LAST_URL, None)
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_DATA, None)
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_RECOMMENDED, None)
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING, None)
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHING, None)
        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_FETCHED_AT, None)

    async def _fetch_orders(self, session_id: str, return_url: str) -> Optional[List[Dict[str, Any]]]:
        token = self._tokens.get_access_token(session_id) if self._tokens else ""
        if not token and self._tokens:
            token = await self._tokens.ensure_access_token(
                session_id,
                return_url=return_url,
                reason="hearbe_order_history_missing_token",
            )
        if not token:
            await self._sender.send_tts_response(session_id, "로그인이 필요합니다. 먼저 로그인해 주세요.")
            return None

        client = OrderClient(backend_url=f"{self._backend_url}/api", jwt_token=token)
        result = await client.get_my_orders()
        if result.get("success"):
            payload = result.get("data") or {}
            data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
            orders = data.get("orders") if isinstance(data, dict) else None
            recs = (
                data.get("recommended_products")
                or data.get("recommendedProducts")
                or []
            ) if isinstance(data, dict) else []
            if isinstance(recs, list):
                recs = [r for r in recs if isinstance(r, dict)]
            else:
                recs = []
            if self._session:
                self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_RECOMMENDED, recs)
            if isinstance(orders, list):
                logger.info("Hearbe orders fetched: session=%s count=%d", session_id, len(orders))
                return [o for o in orders if isinstance(o, dict)]
            logger.info("Hearbe orders fetched: session=%s (no orders list)", session_id)
            return []

        status_code = result.get("status_code")
        if status_code in (401, 403) and self._tokens:
            refreshed = await self._tokens.handle_auth_failure(
                session_id,
                status_code=int(status_code),
                return_url=return_url,
                reason="hearbe_order_history_unauthorized",
            )
            if refreshed:
                client = OrderClient(backend_url=f"{self._backend_url}/api", jwt_token=refreshed)
                retry = await client.get_my_orders()
                if retry.get("success"):
                    payload = retry.get("data") or {}
                    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
                    orders = data.get("orders") if isinstance(data, dict) else None
                    recs = (
                        data.get("recommended_products")
                        or data.get("recommendedProducts")
                        or []
                    ) if isinstance(data, dict) else []
                    if isinstance(recs, list):
                        recs = [r for r in recs if isinstance(r, dict)]
                    else:
                        recs = []
                    if self._session:
                        self._session.set_context(session_id, CTX_HEARBE_ORDER_HISTORY_RECOMMENDED, recs)
                    if isinstance(orders, list):
                        logger.info(
                            "Hearbe orders fetched after refresh: session=%s count=%d",
                            session_id,
                            len(orders),
                        )
                        return [o for o in orders if isinstance(o, dict)]
                    return []

        logger.warning(
            "Hearbe orders fetch failed: session=%s status=%s error=%s",
            session_id,
            str(status_code) if status_code else "n/a",
            result.get("error"),
        )
        await self._sender.send_tts_response(session_id, "주문 내역을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return None


__all__ = [
    "HearbeOrderHistoryHandler",
    "is_hearbe_order_history_url",
    "CTX_HEARBE_ORDER_HISTORY_DATA",
    "CTX_HEARBE_ORDER_HISTORY_RECOMMENDED",
    "CTX_HEARBE_ORDER_HISTORY_PROMPT_PENDING",
]
