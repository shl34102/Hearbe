# -*- coding: utf-8 -*-
"""
Order detail API sender using centralized token manager.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from api.order.order_client import OrderClient, COUPANG_PLATFORM_ID
from api.product.product_client import ProductClient
from ..auth.token_manager import TokenManager
from .order_detail_constants import (
    CTX_ORDER_DETAIL_API_SENT_ID,
    CTX_ORDER_DETAIL_API_PENDING_ID,
    CTX_ORDER_DETAIL_LAST_URL,
    CTX_ORDER_DETAIL_DATA,
)
from .order_detail_utils import build_order_items, get_access_token
from .product_detail_utils import build_product_payload

logger = logging.getLogger(__name__)


class OrderDetailApiSender:
    def __init__(self, sender, session_manager, token_manager: Optional[TokenManager] = None):
        self._sender = sender
        self._session = session_manager
        self._tokens = token_manager

    def handle_token_update(self, session_id: str, access_token: str, refresh_token: str) -> bool:
        if not self._session or not access_token:
            return False
        pending_id = self._session.get_context(session_id, CTX_ORDER_DETAIL_API_PENDING_ID)
        if not pending_id:
            return False
        self._session.set_context(session_id, CTX_ORDER_DETAIL_API_PENDING_ID, None)
        order_data = self._session.get_context(session_id, CTX_ORDER_DETAIL_DATA) or {}
        logger.info(
            "Order API retry after token update: session=%s order_id=%s",
            session_id,
            pending_id,
        )
        asyncio.create_task(self.send_order(session_id, str(pending_id), order_data, force_token=access_token))
        return True

    async def send_order(
        self,
        session_id: str,
        order_id: str,
        order_data: Dict[str, Any],
        force_token: Optional[str] = None,
    ) -> None:
        if not self._session:
            return
        token = force_token or (
            self._tokens.get_access_token(session_id) if self._tokens else get_access_token(self._session, session_id)
        )
        logger.info(
            "Order API send start: session=%s order_id=%s token=%s",
            session_id,
            order_id,
            _format_token(token) if token else "missing",
        )
        if not token:
            if self._tokens:
                return_url = self._session.get_context(session_id, CTX_ORDER_DETAIL_LAST_URL)
                token = await self._tokens.ensure_access_token(
                    session_id,
                    return_url=return_url,
                    reason="order_detail_api_missing_token",
                )
            if not token:
                self._session.set_context(session_id, CTX_ORDER_DETAIL_API_PENDING_ID, order_id)
                return

        items = build_order_items(order_data)
        if not items:
            logger.warning(
                "Order API skipped: no items extracted (session=%s keys=%s)",
                session_id,
                list(order_data.keys()) if isinstance(order_data, dict) else "n/a",
            )
            return

        order_url = self._session.get_context(session_id, CTX_ORDER_DETAIL_LAST_URL) or ""
        client = OrderClient(jwt_token=token)
        result = await client.create_order(
            items=items,
            platform_id=COUPANG_PLATFORM_ID,
            order_url=order_url,
        )
        if result.get("success"):
            self._session.set_context(session_id, CTX_ORDER_DETAIL_API_SENT_ID, order_id)
            logger.info(
                "Order API sent: session=%s order_id=%s items=%d order_url=%s",
                session_id,
                order_id,
                len(items),
                order_url or "missing",
            )
            await self._send_product_if_available(
                session_id=session_id,
                order_id=order_id,
                token=token,
            )
            return

        status_code = result.get("status_code")
        if status_code in (401, 403) and self._tokens:
            return_url = self._session.get_context(session_id, CTX_ORDER_DETAIL_LAST_URL)
            refreshed_token = await self._tokens.handle_auth_failure(
                session_id,
                status_code=status_code,
                return_url=return_url,
                reason="order_detail_api_unauthorized",
            )
            if refreshed_token:
                await self.send_order(session_id, order_id, order_data, force_token=refreshed_token)
                return
            self._session.set_context(session_id, CTX_ORDER_DETAIL_API_PENDING_ID, order_id)
            return

        logger.warning(
            "Order API failed: session=%s order_id=%s error=%s",
            session_id,
            order_id,
            result.get("error"),
        )

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_ORDER_DETAIL_API_SENT_ID, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_API_PENDING_ID, None)

    async def _send_product_if_available(self, *, session_id: str, order_id: str, token: str) -> None:
        if not self._session:
            return
        detail = self._session.get_context(session_id, "product_detail")
        if not isinstance(detail, dict):
            logger.info("Product API skipped: no product_detail (session=%s order_id=%s)", session_id, order_id)
            return

        payload = build_product_payload(detail)
        if not payload:
            logger.info(
                "Product API skipped: incomplete product_detail (session=%s order_id=%s keys=%s)",
                session_id,
                order_id,
                list(detail.keys()),
            )
            return

        logger.info(
            "Product API send start: session=%s order_id=%s token=%s name=%s",
            session_id,
            order_id,
            _format_token(token),
            payload.get("name") or "",
        )
        client = ProductClient(jwt_token=token)
        result = await client.create_product(**payload)
        if result.get("success"):
            logger.info(
                "Product API sent: session=%s order_id=%s status=%s category_depth=%s",
                session_id,
                order_id,
                result.get("status_code"),
                len(payload.get("category_path") or []),
            )
            return

        status_code = result.get("status_code")
        if status_code in (401, 403) and self._tokens:
            return_url = self._session.get_context(session_id, CTX_ORDER_DETAIL_LAST_URL)
            refreshed_token = await self._tokens.handle_auth_failure(
                session_id,
                status_code=status_code,
                return_url=return_url,
                reason="product_api_unauthorized",
            )
            if refreshed_token:
                client = ProductClient(jwt_token=refreshed_token)
                retry = await client.create_product(**payload)
                if retry.get("success"):
                    logger.info(
                        "Product API sent after refresh: session=%s order_id=%s status=%s",
                        session_id,
                        order_id,
                        retry.get("status_code"),
                    )
                    return

        logger.warning(
            "Product API failed: session=%s order_id=%s error=%s",
            session_id,
            order_id,
            result.get("error"),
        )


def _format_token(token: Optional[str]) -> str:
    if not token:
        return ""
    if os.getenv("LOG_TOKEN_FULL", "").strip() == "1":
        return token
    if len(token) <= 12:
        return token
    return f"{token[:6]}...{token[-6:]}"
