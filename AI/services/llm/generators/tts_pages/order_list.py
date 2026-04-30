# -*- coding: utf-8 -*-
"""Order list TTS page wrapper."""

from typing import List, Dict, Any

from api.ws.presenter.pages.order_list import build_order_list_summary_tts as _build


def build_order_list_summary_tts(orders: List[Dict[str, Any]]) -> str:
    return _build(orders or [])
