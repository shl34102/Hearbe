# -*- coding: utf-8 -*-
"""
Search page presenter helpers (TTS formatting).
"""

from typing import List, Tuple, Dict, Any, Optional

from core.korean_product_terms import format_product_terms_for_tts

from ...search.search_reader import build_search_read_tts

MORE_PROMPT_COUNT = "더 읽어드릴까요? '몇 개 더 읽어줘' 또는 '전체 읽어줘'라고 말해 주세요."
MORE_PROMPT_NUMBER = "더 읽어드릴까요? 'n개 더 읽어줘' 또는 '전체 읽어줘'라고 말해 주세요."

NO_DISCOUNT_INFO = "할인율 정보를 찾지 못했습니다."
NO_PRICE_INFO = "가격 정보를 찾지 못했습니다."
NO_TOMORROW_ITEMS = "내일 도착하는 상품을 찾지 못했습니다."
NO_FREE_SHIPPING = "무료배송 상품을 찾지 못했습니다."


def build_search_list_tts(
    products: List[Dict[str, Any]],
    start_index: int,
    count: int,
    include_total: bool,
    more_prompt: str = MORE_PROMPT_COUNT,
) -> Tuple[str, int, bool]:
    tts_text, next_index, has_more = build_search_read_tts(
        products,
        start_index=start_index,
        count=count,
        include_total=include_total
    )
    if has_more:
        tts_text = f"{tts_text} {more_prompt}" if tts_text else more_prompt
    return tts_text, next_index, has_more


def format_highest_discount(name: str, discount_text: Optional[str], price: Optional[str]) -> str:
    name = format_product_terms_for_tts(name)
    msg = f"가장 할인율이 높은 상품은 {name}입니다."
    if discount_text:
        msg += f" 할인율 {discount_text}."
    if price:
        msg += f" 가격 {price}."
    return msg


def format_lowest_price(name: str, price: Optional[str]) -> str:
    name = format_product_terms_for_tts(name)
    msg = f"가장 저렴한 상품은 {name}입니다."
    if price:
        msg += f" 가격 {price}."
    return msg
