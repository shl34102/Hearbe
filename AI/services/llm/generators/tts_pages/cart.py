# -*- coding: utf-8 -*-
"""
Cart TTS page module.
"""

from typing import Any, Dict, List

from api.ws.presenter.pages.cart import build_cart_summary_tts as _build


def build_cart_summary_tts(cart_items: List[Dict[str, Any]], cart_summary: Dict[str, Any]) -> str:
    return _build(cart_items, cart_summary or {})
