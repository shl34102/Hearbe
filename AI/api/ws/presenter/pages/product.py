# -*- coding: utf-8 -*-
"""
Product page presenter helpers.
"""

from typing import Optional

try:
    from services.summarizer import format_for_tts
except ImportError:  # pragma: no cover - optional dependency
    format_for_tts = None


def build_product_summary_tts(product_info) -> Optional[str]:
    if not product_info or not format_for_tts:
        return None
    return format_for_tts(product_info, include_details=True)


def build_ocr_summary_tts(ocr_result) -> Optional[str]:
    if not ocr_result or not getattr(ocr_result, "summary", None):
        return None
    return ocr_result.format_for_tts()
