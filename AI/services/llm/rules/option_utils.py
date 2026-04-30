from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple

from core.korean_numbers import DEFAULT_COUNT_UNITS, replace_korean_number_units


OPTION_KEYWORDS = (
    "옵션",
    "수량",
    "색상",
    "사이즈",
    "크기",
    "용량",
    "중량",
    "팩",
    "개",
)

OPTION_CHANGE_KEYWORDS = (
    "변경",
    "바꿔",
    "바꾸",
    "선택",
    "고르",
    "교체",
    "수정",
)

OPTION_LIST_KEYWORDS = (
    "뭐",
    "어떤",
    "알려",
    "목록",
    "종류",
    "있어",
)

PRICE_KEYWORDS = (
    "가격",
    "얼마",
    "비용",
    "값",
)

PURCHASE_KEYWORDS = (
    "구매",
    "주문",
    "담기",
    "결제",
    "장바구니",
    "카트",
)

_OPTION_QUANTITY_PATTERN = re.compile(
    r"\d+\s*(?:"
    + "|".join(map(re.escape, DEFAULT_COUNT_UNITS))
    + r")"
)


def is_option_related(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in OPTION_KEYWORDS)


def is_option_change_request(text: str) -> bool:
    lowered = replace_korean_number_units(text.lower())
    if any(keyword in lowered for keyword in PURCHASE_KEYWORDS):
        return False
    if any(keyword in lowered for keyword in PRICE_KEYWORDS):
        return False
    if any(keyword in lowered for keyword in OPTION_CHANGE_KEYWORDS):
        return True
    if not is_option_related(lowered):
        return False
    return bool(_OPTION_QUANTITY_PATTERN.search(lowered))


def is_option_list_query(text: str) -> bool:
    lowered = text.lower()
    return is_option_related(lowered) and any(keyword in lowered for keyword in OPTION_LIST_KEYWORDS)


def is_option_price_query(text: str) -> bool:
    lowered = text.lower()
    if not any(keyword in lowered for keyword in PRICE_KEYWORDS):
        return False
    return is_option_related(lowered) or "선택" in lowered


def build_option_list_text(options_list: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(options_list, dict) or not options_list:
        return None
    parts: List[str] = []
    for key, items in options_list.items():
        if not isinstance(items, list):
            continue
        names = [str(item.get("name")) for item in items if isinstance(item, dict) and item.get("name")]
        if not names:
            continue
        if len(options_list) == 1:
            parts.append(", ".join(names))
        else:
            parts.append(f"{key}: " + ", ".join(names))
    if not parts:
        return None
    return "선택 가능한 옵션은 " + " / ".join(parts) + " 입니다."


def find_option_match(
    text: str,
    options_list: Dict[str, Any],
) -> Optional[Tuple[str, Optional[str]]]:
    normalized_text = replace_korean_number_units(text)
    for items in options_list.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            normalized_name = replace_korean_number_units(str(name))
            if normalized_name in normalized_text:
                return str(name), item.get("price")
    return None


def find_selected_prices(options_list: Dict[str, Any]) -> List[Tuple[str, str]]:
    selected: List[Tuple[str, str]] = []
    for items in options_list.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("selected"):
                continue
            name = item.get("name")
            price = item.get("price")
            if name and price:
                selected.append((str(name), str(price)))
    return selected


def list_option_prices(options_list: Dict[str, Any]) -> List[str]:
    parts: List[str] = []
    for items in options_list.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            price = item.get("price")
            if name and price:
                parts.append(f"{name} {price}")
    return parts
