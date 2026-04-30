# -*- coding: utf-8 -*-
"""
Constants for order detail handling.
"""

CTX_ORDER_DETAIL_LAST_URL = "order_detail_last_url"
CTX_ORDER_DETAIL_REQUEST_TYPE = "order_detail_request_type"
CTX_ORDER_DETAIL_PENDING_QUESTION = "order_detail_pending_question"
CTX_ORDER_DETAIL_REQUESTED = "order_detail_requested"
CTX_ORDER_DETAIL_DATA = "order_detail_data"
CTX_ORDER_DETAIL_API_SENT_ID = "order_detail_api_sent_id"
CTX_ORDER_DETAIL_API_RETRY = "order_detail_api_retry"
CTX_ORDER_DETAIL_API_PENDING_ID = "order_detail_api_pending_id"

REQUEST_SUMMARY = "summary"
REQUEST_QUESTION = "question"

ORDER_DETAIL_PROMPT = "주문 상세 페이지에 있는 정보 중 어떤걸 읽어드릴까요?"
ORDER_DETAIL_LOADING_TTS = "주문 상세 정보를 불러오는 중입니다. 잠시만 기다려주세요."
ORDER_DETAIL_NOT_FOUND_TTS = "주문 상세 페이지에서 해당 정보를 찾지 못했어요."

ACTION_LABELS = [
    "장바구니 담기",
    "배송 조회",
    "주문, 배송 취소",
    "주문내역 삭제",
    "주문목록 돌아가기",
]

__all__ = [
    "CTX_ORDER_DETAIL_LAST_URL",
    "CTX_ORDER_DETAIL_REQUEST_TYPE",
    "CTX_ORDER_DETAIL_PENDING_QUESTION",
    "CTX_ORDER_DETAIL_REQUESTED",
    "CTX_ORDER_DETAIL_DATA",
    "CTX_ORDER_DETAIL_API_SENT_ID",
    "CTX_ORDER_DETAIL_API_RETRY",
    "CTX_ORDER_DETAIL_API_PENDING_ID",
    "REQUEST_SUMMARY",
    "REQUEST_QUESTION",
    "ORDER_DETAIL_PROMPT",
    "ORDER_DETAIL_LOADING_TTS",
    "ORDER_DETAIL_NOT_FOUND_TTS",
    "ACTION_LABELS",
]
