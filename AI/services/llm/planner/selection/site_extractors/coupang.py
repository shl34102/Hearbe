"""
Coupang-specific detail extract command builder.
"""

from __future__ import annotations

from typing import Dict, Optional

from core.interfaces import MCPCommand
from ....sites.site_manager import SiteConfig
from .common import build_product_extract_command_common


COUPANG_DEFAULT_SELECTORS: Dict[str, str] = {
    "product_title": "h1.product-title span, h1.product-title",
    "final_price": ".final-price-amount",
    "discount_rate": ".original-price div",
    "quantity_input": ".product-quantity input",
    "option_select": ".option-picker-select",
    "detail_images": ".product-detail-content-inside img",
}


def build_product_extract_command_coupang(
    site: SiteConfig,
    current_url: str = "",
) -> Optional[MCPCommand]:
    return build_product_extract_command_common(
        site,
        current_url=current_url,
        defaults=COUPANG_DEFAULT_SELECTORS,
    )
