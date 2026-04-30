# -*- coding: utf-8 -*-
"""
Order list presenter helpers (TTS formatting).
"""

from typing import List, Dict, Any

from ...order.order_list_reader import build_order_list_read_tts


def build_order_list_summary_tts(orders: List[Dict[str, Any]]) -> str:
    return build_order_list_read_tts(orders or [])
