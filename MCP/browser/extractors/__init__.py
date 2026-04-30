"""
Site-specific extraction dispatchers.
"""

from __future__ import annotations

from typing import List, Dict, Any

from .coupang_search import extract_coupang_search_results
from .coupang_cart import extract_coupang_cart
from .coupang_order_detail import extract_coupang_order_detail
from .coupang_order_list import extract_coupang_order_list


async def extract_search_results_dynamic(page, url: str | None = None) -> List[Dict[str, Any]]:
    """
    Dispatch dynamic extraction by site.
    """
    page_url = url or getattr(page, "url", "") or ""
    if "coupang.com" in page_url:
        return await extract_coupang_search_results(page)
    return []


async def extract_cart_dynamic(page, url: str | None = None) -> Dict[str, Any]:
    """
    Dispatch cart extraction by site.
    """
    page_url = url or getattr(page, "url", "") or ""
    if "coupang.com" in page_url:
        return await extract_coupang_cart(page)
    return {"items": [], "summary": {}}


async def extract_order_detail_dynamic(page, url: str | None = None) -> Dict[str, Any]:
    """
    Dispatch order detail extraction by site.
    """
    page_url = url or getattr(page, "url", "") or ""
    if "coupang.com" in page_url and "/ssr/desktop/order/" in page_url:
        return await extract_coupang_order_detail(page)
    return {}


async def extract_order_list_dynamic(page, url: str | None = None) -> Dict[str, Any]:
    """
    Dispatch order list extraction by site.
    """
    page_url = url or getattr(page, "url", "") or ""
    if "coupang.com" in page_url and "/ssr/desktop/order/list" in page_url:
        return await extract_coupang_order_list(page)
    return {"orders": [], "count": 0}
