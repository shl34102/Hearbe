# -*- coding: utf-8 -*-
"""
Cart page presenter helpers.
"""

from typing import Dict, Any, List

from ...cart.cart_reader import build_cart_read_tts


def build_cart_summary_tts(cart_items: List[Dict[str, Any]], cart_summary: Dict[str, Any]) -> str:
    return build_cart_read_tts(cart_items, cart_summary or {})
