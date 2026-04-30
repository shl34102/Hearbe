"""
Site-specific detail extract command builders.
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import MCPCommand
from .common import build_product_extract_command_common
from .coupang import build_product_extract_command_coupang
from ....sites.site_manager import SiteConfig


def build_product_extract_command_for_site(
    site: Optional[SiteConfig],
    current_url: str = "",
) -> Optional[MCPCommand]:
    if not site:
        return None
    if site.site_id == "coupang":
        return build_product_extract_command_coupang(site, current_url=current_url)
    return build_product_extract_command_common(site, current_url=current_url)
