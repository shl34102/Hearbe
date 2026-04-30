# -*- coding: utf-8 -*-
"""
Order sync service.

Orchestrates order extraction from Coupang and sync to backend.
Triggered after checkout completion.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from .order_client import OrderClient, OrderItem, COUPANG_PLATFORM_ID
    from .order_extractor import OrderExtractor, extract_orders_from_page_data
except ImportError:
    from order_client import OrderClient, OrderItem, COUPANG_PLATFORM_ID
    from order_extractor import OrderExtractor, extract_orders_from_page_data

logger = logging.getLogger(__name__)

# Coupang order history URLs
COUPANG_ORDER_LIST_URL = "https://mc.coupang.com/ssr/desktop/order/list"
COUPANG_ORDER_LIST_ALT = "https://www.coupang.com/np/orders"


@dataclass
class SyncResult:
    """Result of order sync operation."""
    success: bool
    synced_count: int = 0
    items: List[OrderItem] = None
    error: Optional[str] = None
    backend_response: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []


class OrderSyncService:
    """
    Service to sync Coupang orders to backend.

    Flow:
    1. Navigate to Coupang order page (via MCP)
    2. Extract HTML from page
    3. Parse order items
    4. POST to backend /orders API

    Usage:
        sync_service = OrderSyncService()

        # With MCP navigate function
        result = await sync_service.sync_latest_orders(
            navigate_fn=mcp_navigate,
            extract_fn=mcp_extract_html,
        )

        # Or with pre-fetched HTML
        result = await sync_service.sync_from_html(html_content)

        # Or with pre-parsed items
        result = await sync_service.sync_items(items)
    """

    def __init__(
        self,
        backend_url: str = None,
        jwt_token: Optional[str] = None,
        chrome_profile_path: Optional[Path] = None,
    ):
        self._client = OrderClient(
            backend_url=backend_url or "https://i14d108.p.ssafy.io/A",
            jwt_token=jwt_token,
            chrome_profile_path=chrome_profile_path,
        )
        self._extractor = OrderExtractor()

    async def sync_latest_orders(
        self,
        navigate_fn: Callable[[str], Any] = None,
        extract_fn: Callable[[], str] = None,
        page_data: Dict[str, Any] = None,
        max_items: int = 10,
    ) -> SyncResult:
        """
        Full sync flow: navigate -> extract -> parse -> send.

        Args:
            navigate_fn: Async function to navigate browser to URL
            extract_fn: Async function to extract HTML from current page
            page_data: Pre-fetched page data (alternative to navigate/extract)
            max_items: Maximum items to sync (most recent)

        Returns:
            SyncResult with status and synced items
        """
        try:
            # Option 1: Use pre-fetched page data
            if page_data:
                items = extract_orders_from_page_data(page_data)
                if items:
                    return await self.sync_items(items[:max_items])
                return SyncResult(success=False, error="No orders found in page data")

            # Option 2: Use navigate + extract functions
            if navigate_fn and extract_fn:
                # Navigate to order list page
                logger.info("Navigating to Coupang order list: %s", COUPANG_ORDER_LIST_URL)
                await navigate_fn(COUPANG_ORDER_LIST_URL)

                # Wait for page load
                await asyncio.sleep(2)

                # Extract HTML
                html = await extract_fn()
                if html:
                    return await self.sync_from_html(html, max_items=max_items)
                return SyncResult(success=False, error="Failed to extract HTML from order page")

            return SyncResult(
                success=False,
                error="Either page_data or navigate_fn+extract_fn required"
            )

        except Exception as e:
            logger.error("Order sync failed: %s", e)
            return SyncResult(success=False, error=str(e))

    async def sync_from_html(self, html: str, max_items: int = 10) -> SyncResult:
        """
        Parse HTML and sync extracted orders.

        Args:
            html: Raw HTML from Coupang order page
            max_items: Maximum items to sync

        Returns:
            SyncResult with status
        """
        try:
            orders = self._extractor.extract_from_html(html)
            if not orders:
                return SyncResult(success=False, error="No orders extracted from HTML")

            # Flatten all items from all orders
            all_items = []
            for order in orders:
                all_items.extend(order.items)

            if not all_items:
                return SyncResult(success=False, error="No items found in orders")

            # Limit to most recent items
            items_to_sync = all_items[:max_items]
            return await self.sync_items(items_to_sync)

        except Exception as e:
            logger.error("HTML sync failed: %s", e)
            return SyncResult(success=False, error=str(e))

    async def sync_items(
        self,
        items: List[OrderItem],
        platform_id: int = COUPANG_PLATFORM_ID,
    ) -> SyncResult:
        """
        Sync pre-parsed order items to backend.

        Args:
            items: List of OrderItem to sync
            platform_id: Platform ID (1 = Coupang)

        Returns:
            SyncResult with backend response
        """
        if not items:
            return SyncResult(success=False, error="No items to sync")

        try:
            logger.info("Syncing %d order items to backend", len(items))

            response = await self._client.create_order(
                items=items,
                platform_id=platform_id,
            )

            if response.get("success"):
                return SyncResult(
                    success=True,
                    synced_count=len(items),
                    items=items,
                    backend_response=response.get("data"),
                )
            else:
                return SyncResult(
                    success=False,
                    error=response.get("error", "Unknown error"),
                    backend_response=response,
                )

        except Exception as e:
            logger.error("Items sync failed: %s", e)
            return SyncResult(success=False, error=str(e))

    async def sync_from_mcp_result(self, mcp_result: Dict[str, Any]) -> SyncResult:
        """
        Sync orders from MCP execution result.

        Integration point for MCPHandler after checkout.

        Args:
            mcp_result: MCP result dict containing page_data or HTML

        Returns:
            SyncResult with status
        """
        page_data = mcp_result.get("page_data") or {}
        result = mcp_result.get("result") or {}

        # Try page_data first
        if page_data:
            items = extract_orders_from_page_data(page_data)
            if items:
                return await self.sync_items(items)

        # Try result
        if result:
            items = extract_orders_from_page_data(result)
            if items:
                return await self.sync_items(items)

        # Try HTML extraction
        html = page_data.get("html") or result.get("html")
        if html:
            return await self.sync_from_html(html)

        return SyncResult(success=False, error="No order data in MCP result")


# Singleton instance for easy access
_sync_service: Optional[OrderSyncService] = None


def get_order_sync_service() -> OrderSyncService:
    """Get or create singleton OrderSyncService instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = OrderSyncService()
    return _sync_service


async def sync_orders_after_checkout(page_data: Dict[str, Any]) -> SyncResult:
    """
    Convenience function to sync orders after checkout.

    Called from checkout flow after payment completion.

    Args:
        page_data: Page data from order confirmation or order list page

    Returns:
        SyncResult with status
    """
    service = get_order_sync_service()
    return await service.sync_latest_orders(page_data=page_data)
