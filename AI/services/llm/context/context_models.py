# -*- coding: utf-8 -*-
"""
Page context models and page type detection.

Important: Prefer site config-based page type detection (services.llm.sites.site_manager)
to keep multi-platform behavior consistent (Coupang vs Hearbe).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..sites.site_manager import SiteConfig


@dataclass
class PageContext:
    """Current page context."""

    site_name: str
    page_type: str  # main, search, product, cart, login, orderlist, orderdetail, ...
    available_actions: List[str]
    selectors: Dict[str, str]


# Cross-page actions (intents) we want to support from anywhere.
# Note: Some of these are implemented via pre-navigation (e.g., search from cart/home).
COMMON_ACTIONS = ["navigate", "scroll", "click", "go_to_cart", "go_to_order_list", "search"]

PAGE_SPECIFIC_ACTIONS = {
    "main": ["search", "login"],
    "search": ["select_product", "next_page", "filter", "sort"],
    "product": ["add_to_cart", "buy_now", "view_reviews"],
    "cart": ["checkout", "remove_item", "change_quantity", "continue_shopping"],
    "orderlist": ["open_order_detail", "search_order"],
    "orderdetail": ["order_detail_actions"],
    "login": ["submit_login", "find_id", "find_password", "signup"],
    "mall": ["browse", "open_item"],
    "member_info": [],
    "order_history": [],
    "hearbe_cart": [],
    "unknown": [],
}


def get_available_actions(page_type: str) -> List[str]:
    """Get available actions for a page type (common + page-specific)."""
    specific = PAGE_SPECIFIC_ACTIONS.get(page_type, [])
    return COMMON_ACTIONS + specific


def _detect_page_type_fallback(url: str) -> str:
    """Best-effort page type inference when site config does not match."""
    if not url:
        return "main"
    url_lower = url.lower()

    if "login" in url_lower or "signin" in url_lower:
        return "login"
    if "/search" in url_lower or "query=" in url_lower or "keyword=" in url_lower:
        return "search"
    if "/vp/" in url_lower or "/products/" in url_lower or "/item" in url_lower:
        return "product"
    if "/cart" in url_lower:
        return "cart"
    if "/ssr/desktop/order/list" in url_lower:
        return "orderlist"
    if "/ssr/desktop/order/" in url_lower:
        return "orderdetail"
    if "/checkout" in url_lower:
        return "checkout"
    return "main"


def get_page_context(url: str, site: Optional[SiteConfig] = None) -> PageContext:
    """Build page context from URL and site config."""
    page_type = site.detect_page_type(url) if site else None
    if not page_type:
        page_type = _detect_page_type_fallback(url)

    site_name = site.name if site else "unknown"

    selectors: Dict[str, str] = {}
    if site:
        page_selectors = site.get_page_selectors(page_type)
        if page_selectors:
            selectors = page_selectors.selectors

    available_actions = get_available_actions(page_type)

    return PageContext(
        site_name=site_name,
        page_type=page_type,
        available_actions=available_actions,
        selectors=selectors,
    )
