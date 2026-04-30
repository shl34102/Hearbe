# -*- coding: utf-8 -*-
"""
Search results insights helpers (price/discount/delivery).
"""

import re
from typing import Dict, Any, Iterable, Optional, Tuple, List

from core.korean_numbers import extract_ordinal_index as _extract_ordinal_index


def get_name(item: Dict[str, Any]) -> str:
    return (
        item.get("name")
        or item.get("title")
        or item.get("product_name")
        or "상품"
    )


def _get_field(item: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = item.get(key)
        if value:
            return str(value)
    return ""


def normalize_price_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()
    match = re.search(r"\d{1,3}(?:,\d{3})+\s*원|\d+\s*원", text)
    if match:
        return match.group(0).replace(" ", "")
    match = re.search(r"\d{1,3}(?:,\d{3})+", text)
    if match:
        return match.group(0) + "원"
    match = re.search(r"\d+", text)
    if match:
        return match.group(0) + "원"
    return ""


def parse_price_value(text: str) -> Optional[int]:
    if not text:
        return None
    digits = re.findall(r"\d+", str(text))
    if not digits:
        return None
    return int("".join(digits))


def normalize_discount_text(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"\d+\s*%", str(text))
    if match:
        return match.group(0).replace(" ", "")
    match = re.search(r"\d+", str(text))
    if match:
        return match.group(0) + "%"
    return ""


def parse_discount_value(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"\d+", str(text))
    return int(match.group(0)) if match else None


def get_price_text(item: Dict[str, Any]) -> str:
    raw = _get_field(item, ["price", "product_price", "final_price"])
    return normalize_price_text(raw)


def get_discount_text(item: Dict[str, Any]) -> str:
    raw = _get_field(item, ["discount", "discount_rate", "product_discount"])
    return normalize_discount_text(raw)


def get_delivery_text(item: Dict[str, Any]) -> str:
    return _get_field(item, ["delivery", "arrival", "product_delivery", "arrival_info"])


def normalize_rating_text(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"\d+(?:\.\d+)?", str(text))
    return match.group(0) if match else ""


def get_rating_text(item: Dict[str, Any]) -> str:
    raw = _get_field(item, ["rating", "product_rating"])
    value = normalize_rating_text(raw)
    return f"{value}점" if value else ""


def is_tomorrow_delivery(item: Dict[str, Any]) -> bool:
    text = get_delivery_text(item)
    return "내일" in text if text else False


def is_free_shipping(item: Dict[str, Any]) -> bool:
    value = item.get("free_shipping")
    if isinstance(value, bool):
        return value
    if value and "무료배송" in str(value):
        return True
    text = _get_field(item, ["delivery", "arrival", "product_delivery", "arrival_info"])
    return "무료배송" in text if text else False


def is_free_return(item: Dict[str, Any]) -> bool:
    value = item.get("free_return")
    if isinstance(value, bool):
        return value
    if value and "무료반품" in str(value):
        return True
    return False


def extract_ordinal_index(text: str) -> Optional[int]:
    return _extract_ordinal_index(text)


def find_lowest_price_item(
    items: List[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    best_item = None
    best_price = None
    for item in items:
        price_text = _get_field(item, ["price", "product_price", "final_price"])
        price_val = parse_price_value(price_text)
        if price_val is None:
            continue
        if best_price is None or price_val < best_price:
            best_price = price_val
            best_item = item
    return best_item, best_price


def find_highest_discount_item(
    items: List[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    best_item = None
    best_discount = None
    for item in items:
        discount_text = _get_field(item, ["discount", "discount_rate", "product_discount"])
        discount_val = parse_discount_value(discount_text)
        if discount_val is None:
            continue
        if best_discount is None or discount_val > best_discount:
            best_discount = discount_val
            best_item = item
    return best_item, best_discount


def filter_tomorrow_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in items if is_tomorrow_delivery(item)]


def filter_free_shipping_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in items if is_free_shipping(item)]
