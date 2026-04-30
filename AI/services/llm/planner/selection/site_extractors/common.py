"""
Common product detail extract command builder.
"""

from __future__ import annotations

from typing import Dict, Optional

from core.interfaces import MCPCommand
from ....sites.site_manager import SiteConfig


def build_product_extract_command_common(
    site: SiteConfig,
    current_url: str = "",
    defaults: Optional[Dict[str, str]] = None,
) -> Optional[MCPCommand]:
    page = site.get_page_selectors("product")
    selectors = page.selectors if page and page.selectors else {}
    merged = _merge_selectors(selectors, defaults)
    return _build_extract_command_from_selectors(merged)


def _merge_selectors(selectors: Dict[str, str], defaults: Optional[Dict[str, str]]) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    if defaults:
        merged.update(defaults)
    merged.update(selectors or {})
    return merged


def _build_extract_command_from_selectors(
    selectors: Dict[str, str],
) -> Optional[MCPCommand]:
    field_selectors: Dict[str, str] = {}
    field_attributes: Dict[str, str] = {}

    title_selector = selectors.get("product_title")
    if title_selector:
        field_selectors["name"] = title_selector

    price_selector = selectors.get("final_price") or selectors.get("price")
    if price_selector:
        field_selectors["price"] = price_selector

    discount_selector = selectors.get("discount_rate") or selectors.get("original_price")
    if discount_selector:
        field_selectors["discount"] = discount_selector

    info_selector = selectors.get("product_info")
    if info_selector:
        field_selectors["description"] = info_selector

    quantity_selector = selectors.get("quantity_input")
    if quantity_selector:
        field_selectors["quantity"] = quantity_selector
        field_attributes["quantity"] = "value"

    option_selector = selectors.get("option_select")
    if option_selector:
        field_selectors["option"] = option_selector

    image_selector = selectors.get("detail_images")

    if not field_selectors and not image_selector:
        return None

    fields = list(field_selectors.keys())
    return MCPCommand(
        tool_name="extract_detail",
        arguments={
            "fields": fields,
            "field_selectors": field_selectors,
            "field_attributes": field_attributes,
            "image_selector": image_selector,
            "image_attribute": "src",
            "image_limit": 80,
            "fallback_dynamic": True,
        },
        description="extract product detail fields"
    )
