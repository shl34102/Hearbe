# -*- coding: utf-8 -*-
"""
Search TTS page module.
"""

from typing import Any, Dict, List, Tuple, Optional

from api.ws.presenter.pages.search import (
    build_search_list_tts as _build_list,
    MORE_PROMPT_COUNT,
    MORE_PROMPT_NUMBER,
    NO_DISCOUNT_INFO,
    NO_PRICE_INFO,
    NO_TOMORROW_ITEMS,
    NO_FREE_SHIPPING,
    format_highest_discount as _format_highest_discount,
    format_lowest_price as _format_lowest_price,
)


def build_search_list_tts(
    products: List[Dict[str, Any]],
    start_index: int,
    count: int,
    include_total: bool,
    more_prompt: str = MORE_PROMPT_COUNT,
) -> Tuple[str, int, bool]:
    return _build_list(products, start_index, count, include_total, more_prompt)


def format_highest_discount(name: str, discount_text: Optional[str], price: Optional[str]) -> str:
    return _format_highest_discount(name, discount_text, price)


def format_lowest_price(name: str, price: Optional[str]) -> str:
    return _format_lowest_price(name, price)
