# -*- coding: utf-8 -*-
"""
Product TTS page module.
"""

from typing import Optional

from api.ws.presenter.pages.product import build_product_summary_tts as _build_summary
from api.ws.presenter.pages.product import build_ocr_summary_tts as _build_ocr


def build_product_summary_tts(product_info) -> Optional[str]:
    return _build_summary(product_info)


def build_ocr_summary_tts(ocr_result) -> Optional[str]:
    return _build_ocr(ocr_result)
