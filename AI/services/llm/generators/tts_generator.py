# -*- coding: utf-8 -*-
"""
TTS generator that delegates to page-specific modules.
"""

from typing import Any, Dict, List, Optional, Tuple

# Keep these constants local to avoid circular imports during startup.
MORE_PROMPT_COUNT = "더 읽어드릴까요? '몇 개 더 읽어줘' 또는 '전체 읽어줘'라고 말해 주세요."
MORE_PROMPT_NUMBER = "몇 개 더 읽어드릴까요?"
NO_DISCOUNT_INFO = "할인율 정보를 찾지 못했습니다."
NO_PRICE_INFO = "가격 정보를 찾지 못했습니다."
NO_TOMORROW_ITEMS = "내일 도착하는 상품을 찾지 못했습니다."
NO_FREE_SHIPPING = "무료배송 상품을 찾지 못했습니다."


class TTSGenerator:
    def build_cart_summary(
        self,
        cart_items: List[Dict[str, Any]],
        cart_summary: Dict[str, Any],
    ) -> str:
        from .tts_pages.cart import build_cart_summary_tts
        return build_cart_summary_tts(cart_items, cart_summary or {})

    def build_order_list_summary(
        self,
        orders: List[Dict[str, Any]],
    ) -> str:
        from .tts_pages.order_list import build_order_list_summary_tts
        return build_order_list_summary_tts(orders or [])

    def build_search_list(
        self,
        products: List[Dict[str, Any]],
        start_index: int,
        count: int,
        include_total: bool,
        more_prompt: str = MORE_PROMPT_COUNT,
    ) -> Tuple[str, int, bool]:
        from .tts_pages.search import build_search_list_tts
        return build_search_list_tts(products, start_index, count, include_total, more_prompt)

    def build_product_summary(self, product_info) -> Optional[str]:
        from .tts_pages.product import build_product_summary_tts
        return build_product_summary_tts(product_info)

    def build_ocr_summary(self, ocr_result) -> Optional[str]:
        from .tts_pages.product import build_ocr_summary_tts
        return build_ocr_summary_tts(ocr_result)

    def build_login_success(self, current_url: str) -> str:
        from .tts_pages.login import build_login_success_tts
        return build_login_success_tts(current_url)

    def build_login_autofill_success(self, current_url: str) -> str:
        from .tts_pages.login import build_login_autofill_success_tts
        return build_login_autofill_success_tts(current_url)

    def build_login_guidance(self, active_method: Optional[str] = None) -> str:
        from .tts_pages.login import build_login_guidance_tts
        return build_login_guidance_tts(active_method)

    def build_captcha_prompt(self) -> str:
        from .tts_pages.login import build_captcha_prompt_tts
        return build_captcha_prompt_tts()

    def build_hearbe_main_guidance(self) -> str:
        from .tts_pages.hearbe import build_hearbe_main_guidance_tts
        return build_hearbe_main_guidance_tts()

    def build_hearbe_login_redirect(self) -> str:
        from .tts_pages.hearbe import build_hearbe_login_redirect_tts
        return build_hearbe_login_redirect_tts()

    def build_hearbe_mall_guidance(self) -> str:
        from .tts_pages.hearbe import build_hearbe_mall_guidance_tts
        return build_hearbe_mall_guidance_tts()


__all__ = [
    "TTSGenerator",
    "MORE_PROMPT_COUNT",
    "MORE_PROMPT_NUMBER",
    "NO_DISCOUNT_INFO",
    "NO_PRICE_INFO",
    "NO_TOMORROW_ITEMS",
    "NO_FREE_SHIPPING",
]
