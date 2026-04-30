# -*- coding: utf-8 -*-
"""
Summarizer Service

HTML 파싱 및 상품 정보 요약 모듈
OCR 통합 서비스 포함
"""

from .html_parser import (
    CoupangHTMLParser,
    NaverHTMLParser,
    ProductInfo,
    parse_product_html,
    format_for_tts,
    format_summary_for_tts,
    detect_site,
)

from .ocr_integrator import (
    OCRIntegrator,
    OCRChunkResult,
    get_ocr_integrator,
)

__all__ = [
    # HTML Parser
    "CoupangHTMLParser",
    "NaverHTMLParser",
    "ProductInfo",
    "parse_product_html",
    "format_for_tts",
    "format_summary_for_tts",
    "detect_site",
    # OCR Integrator
    "OCRIntegrator",
    "OCRChunkResult",
    "get_ocr_integrator",
]
