# -*- coding: utf-8 -*-
"""
Helpers for syncing extracted product_detail to backend.
"""

import re
from typing import Any, Dict, List, Optional

COUPANG_PRODUCT_NUMBER_KEY = "쿠팡상품번호"


def extract_coupang_product_number(product_detail: Dict[str, Any]) -> str:
    """
    Returns a string like "7689270513 - 20972233691" if present.
    """
    if not isinstance(product_detail, dict):
        return ""

    kv = product_detail.get("coupang_product_info_kv")
    if isinstance(kv, dict):
        value = kv.get(COUPANG_PRODUCT_NUMBER_KEY) or kv.get(COUPANG_PRODUCT_NUMBER_KEY.replace("상품", " 상품"))
        if isinstance(value, str) and value.strip():
            return value.strip()

    info = product_detail.get("coupang_product_info")
    if isinstance(info, list):
        for line in info:
            text = str(line or "").strip()
            if not text:
                continue
            if COUPANG_PRODUCT_NUMBER_KEY in text:
                # Common formats:
                # - "쿠팡상품번호: 768... - 209..."
                # - "쿠팡상품번호 768... - 209..."
                m = re.search(r"쿠팡상품번호\s*[:：]?\s*(.+)$", text)
                if m:
                    return m.group(1).strip()
                return text

    return ""


def normalize_category_path(category_path: Any) -> List[str]:
    if not isinstance(category_path, list):
        return []
    out: List[str] = []
    for part in category_path:
        s = str(part or "").strip()
        if s:
            out.append(s)
    return out


def build_product_payload(product_detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Builds the request payload for POST /api/product.

    Required:
    - name
    - category_path

    Optional:
    - coupang_product_number
    """
    if not isinstance(product_detail, dict):
        return None

    name = str(product_detail.get("name") or "").strip()
    if not name:
        return None

    category_path = normalize_category_path(product_detail.get("category_path"))
    if not category_path:
        # Keep it strict for now to avoid syncing low-signal payloads.
        return None

    coupang_product_number = extract_coupang_product_number(product_detail)
    payload: Dict[str, Any] = {
        "name": name,
        "category_path": category_path,
    }
    if coupang_product_number:
        payload["coupang_product_number"] = coupang_product_number
    return payload


__all__ = [
    "build_product_payload",
    "extract_coupang_product_number",
    "normalize_category_path",
]

