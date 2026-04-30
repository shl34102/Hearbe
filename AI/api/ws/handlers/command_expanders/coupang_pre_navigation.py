# -*- coding: utf-8 -*-
"""
Coupang-specific command expansion.
"""

from typing import List, Optional
from urllib.parse import urlparse

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_site_manager, SiteConfig


# Only explicit Coupang terms should trigger Coupang pre-navigation.
COUPANG_PRENAV_TERMS = ("마이쿠팡", "쿠팡")
NAV_TOOLS = {"goto", "navigate_to_url"}


def expand_coupang_pre_navigation(commands: List, current_url: str) -> List:
    """
    If a Coupang-specific click_text appears while not on Coupang,
    prepend a navigate+wait sequence to ensure correct context.
    """
    if not commands:
        return commands

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
            description="쿠팡 이동",
        ),
        MCPCommand(
            tool_name="wait",
            arguments={"ms": 1000},
            description="페이지 로딩 대기",
        ),
    ]
    return injected + list(commands)


def _get_site(site_id: str) -> Optional[SiteConfig]:
    manager = get_site_manager()
    return manager.get_site(site_id) if manager else None


def _is_on_site(current_url: str, site: SiteConfig) -> bool:
    return bool(current_url and site and site.matches_domain(current_url))


def _has_coupang_click(commands: List) -> bool:
    for cmd in commands:
        tool = _get_tool_name(cmd)
        if tool != "click_text":
            continue
        text = str(_get_args(cmd).get("text", "") or "")
        if any(term in text for term in COUPANG_PRENAV_TERMS):
            return True
    return False


def _has_navigation_to_site(commands: List, site: SiteConfig) -> bool:
    for cmd in commands:
        tool = _get_tool_name(cmd)
        if tool not in NAV_TOOLS:
            continue
        url = str(_get_args(cmd).get("url", "") or "")
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


def _get_tool_name(cmd) -> str:
    if hasattr(cmd, "tool_name"):
        return cmd.tool_name or ""
    if isinstance(cmd, dict):
        return cmd.get("tool_name", "") or ""
    return ""


def _get_args(cmd) -> dict:
    if hasattr(cmd, "arguments"):
        return cmd.arguments or {}
    if isinstance(cmd, dict):
        return cmd.get("arguments", {}) or {}
    return {}
