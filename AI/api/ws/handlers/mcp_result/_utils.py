# -*- coding: utf-8 -*-
"""
Shared utilities for MCP result processing.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urljoin


def extract_request_ts(request_id: Optional[str]) -> Optional[float]:
    """Extract timestamp from request_id format: '{uuid}_{ts}_{index}'."""
    if not request_id:
        return None
    parts = request_id.split("_")
    if len(parts) < 3:
        return None
    try:
        return float(parts[-2])
    except ValueError:
        return None


def normalize_image_urls(urls: List[str], base_url: Optional[str] = None) -> List[str]:
    """Normalize and deduplicate image URLs."""
    if not urls:
        return []
    seen = set()
    normalized: List[str] = []
    for raw in urls:
        if not isinstance(raw, str):
            continue
        url = raw.strip()
        if not url:
            continue
        if url.startswith(("data:", "blob:", "javascript:")):
            continue
        if url.startswith("//"):
            url = f"https:{url}"
        elif url.startswith("/") and base_url:
            url = urljoin(base_url, url)
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        normalized.append(url)
    return normalized
