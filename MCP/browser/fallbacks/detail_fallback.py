"""
Detail extraction fallback helpers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from browser.extractors.coupang_product import (
    extract_coupang_product_extras,
    extract_coupang_product_options,
)


async def apply_detail_option_fallback(page, detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    page_url = page.url or ""
    if "coupang.com" not in page_url:
        return None

    merged: Dict[str, Any] = {}

    dynamic_options = await extract_coupang_product_options(page)
    if dynamic_options:
        merged.update(dynamic_options if isinstance(dynamic_options, dict) else {})

        selected = dynamic_options.get("selected") if isinstance(dynamic_options, dict) else None
        options_list = dynamic_options.get("options_list") if isinstance(dynamic_options, dict) else None

        if selected and not detail.get("options"):
            detail["options"] = selected
        elif isinstance(dynamic_options, dict) and not detail.get("options"):
            detail["options"] = dynamic_options

        if options_list and not detail.get("options_list"):
            detail["options_list"] = options_list

    extras = await extract_coupang_product_extras(page)
    if isinstance(extras, dict) and extras:
        merged.update(extras)
        # Only populate fields when missing to avoid overriding explicit selectors.
        for key, value in extras.items():
            if value and detail.get(key) in (None, "", [], {}):
                detail[key] = value

    return merged or None
