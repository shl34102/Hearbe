"""
Search extraction fallback helpers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from browser.extractors import extract_search_results_dynamic


async def build_search_fallback_result(page, limit: int) -> Optional[Dict[str, Any]]:
    products = await extract_search_results_dynamic(page)
    if not products:
        return None
    sliced = products if limit <= 0 else products[:limit]
    return {
        "success": True,
        "products": sliced,
        "count": len(sliced),
        "page_url": page.url,
        "fallback": "dynamic",
    }
