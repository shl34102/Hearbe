# -*- coding: utf-8 -*-
"""
Coupang command guards.

- Inject pre-navigation to Coupang when explicit Coupang click_text appears
  outside Coupang pages.
- Restrict order-cancel actions to Coupang order detail page only.
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_current_site, get_page_type, get_site_manager, SiteConfig

from .patterns import is_order_cancel_command
from .utils import get_args, get_tool_name

logger = logging.getLogger(__name__)


COUPANG_PRENAV_TERMS = ("마이쿠팡", "쿠팡")
NAV_TOOLS = {"goto", "navigate_to_url"}


def apply_coupang_guards(commands: List, current_url: str) -> List:
    if not commands:
        return commands
    guarded = _inject_coupang_pre_navigation(commands, current_url)
    guarded = _restrict_order_cancel_scope(guarded, current_url)
    return guarded


def _inject_coupang_pre_navigation(commands: List, current_url: str) -> List:
    coupang = _get_site("coupang")
    if not coupang:
        return commands
    if _is_on_site(current_url, coupang):
        return commands
    if not _has_coupang_click(commands):
        return commands
    if _has_navigation_to_site(commands, coupang):
        return commands

    home_url = coupang.get_url("home") or "https://www.coupang.com/"
    injected = [
        MCPCommand(
            tool_name="goto",
            arguments={"url": home_url},
            description="navigate to Coupang",
        ),
        MCPCommand(
            tool_name="wait",
            arguments={"ms": 1000},
            description="wait for page load",
        ),
    ]
    logger.info("Command guard(coupang): pre-navigation injected")
    return injected + list(commands)


def _restrict_order_cancel_scope(commands: List, current_url: str) -> List:
    is_coupang_orderdetail = _is_coupang_orderdetail(current_url)
    if is_coupang_orderdetail:
        return commands

    filtered = []
    removed = 0
    for cmd in commands:
        if is_order_cancel_command(cmd):
            removed += 1
            continue
        filtered.append(cmd)
    if removed:
        logger.info(
            "Command guard(coupang): removed %d order-cancel command(s) outside coupang orderdetail",
            removed,
        )
    return filtered


def _is_coupang_orderdetail(current_url: str) -> bool:
    if not current_url:
        return False
    site = get_current_site(current_url)
    if not site or getattr(site, "site_id", "") != "coupang":
        return False
    return get_page_type(current_url) == "orderdetail"

def _get_site(site_id: str) -> Optional[SiteConfig]:
    manager = get_site_manager()
    return manager.get_site(site_id) if manager else None


def _is_on_site(current_url: str, site: SiteConfig) -> bool:
    return bool(current_url and site and site.matches_domain(current_url))


def _has_coupang_click(commands: List) -> bool:
    for cmd in commands:
        if get_tool_name(cmd) != "click_text":
            continue
        text = str(get_args(cmd).get("text", "") or "")
        if any(term in text for term in COUPANG_PRENAV_TERMS):
            return True
    return False


def _has_navigation_to_site(commands: List, site: SiteConfig) -> bool:
    for cmd in commands:
        tool = get_tool_name(cmd)
        if tool not in NAV_TOOLS:
            continue
        url = str(get_args(cmd).get("url", "") or "")
        if not url:
            continue
        if site.matches_domain(url):
            return True
        try:
            host = urlparse(url).netloc.lower()
        except Exception:
            host = ""
        if any(domain in host for domain in site.domains):
            return True
    return False


__all__ = ["apply_coupang_guards"]
