# -*- coding: utf-8 -*-
"""
Order detail handler.

Extracts and announces order detail info on order detail pages,
and answers user questions using extracted data.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from core.interfaces import MCPCommand
from services.llm.generators.llm_generator import LLMGenerator

from ..auth.token_manager import TokenManager
from ..utils.temp_file_manager import TempFileManager
from .order_detail_api import OrderDetailApiSender
from .order_detail_constants import (
    CTX_ORDER_DETAIL_LAST_URL,
    CTX_ORDER_DETAIL_REQUEST_TYPE,
    CTX_ORDER_DETAIL_PENDING_QUESTION,
    CTX_ORDER_DETAIL_REQUESTED,
    CTX_ORDER_DETAIL_DATA,
    CTX_ORDER_DETAIL_API_SENT_ID,
    REQUEST_SUMMARY,
    REQUEST_QUESTION,
    ORDER_DETAIL_PROMPT,
    ORDER_DETAIL_LOADING_TTS,
    ORDER_DETAIL_NOT_FOUND_TTS,
)
from .order_detail_utils import (
    resolve_page_url,
    is_order_detail_url,
    extract_order_id_from_order_detail_url,
    is_order_detail_question,
    is_order_detail_read_request,
    build_order_detail_summary,
    build_order_detail_actions,
    build_order_detail_payment_tts,
    prune_data,
    truncate_text,
)

logger = logging.getLogger(__name__)


class OrderDetailHandler:
    def __init__(
        self,
        sender,
        session_manager,
        llm_generator: Optional[LLMGenerator] = None,
        token_manager: Optional[TokenManager] = None,
    ):
        self._sender = sender
        self._session = session_manager
        self._llm = llm_generator or LLMGenerator()
        self._api_sender = OrderDetailApiSender(sender, session_manager, token_manager=token_manager)
        self._file_manager = TempFileManager()

    def handle_token_update(self, session_id: str, access_token: str, refresh_token: str) -> bool:
        return self._api_sender.handle_token_update(session_id, access_token, refresh_token)

    async def handle_page_update(self, session_id: str, current_url: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not is_order_detail_url(current_url):
            return False

        last_url = self._session.get_context(session_id, CTX_ORDER_DETAIL_LAST_URL)
        if last_url == current_url and self._session.get_context(session_id, CTX_ORDER_DETAIL_DATA):
            return False

        self._session.set_context(session_id, CTX_ORDER_DETAIL_LAST_URL, current_url)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUEST_TYPE, REQUEST_SUMMARY)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_PENDING_QUESTION, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUESTED, True)
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="extract_order_detail",
                    arguments={},
                    description="extract order detail",
                )
            ],
        )
        return True

    async def ensure_context(self, session_id: str, current_url: str, session) -> bool:
        if not self._sender or not self._session:
            return False
        if not current_url or not is_order_detail_url(current_url):
            return False
        if self._session.get_context(session_id, CTX_ORDER_DETAIL_DATA):
            return False
        if self._session.get_context(session_id, CTX_ORDER_DETAIL_REQUESTED):
            return False

        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUEST_TYPE, REQUEST_SUMMARY)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_PENDING_QUESTION, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUESTED, True)
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="extract_order_detail",
                    arguments={},
                    description="extract order detail",
                )
            ],
        )
        return True

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not text:
            return False
        session = self._session.get_session(session_id)
        current_url = session.current_url if session else ""
        if not is_order_detail_url(current_url):
            return False

        if self._session.get_context(session_id, CTX_ORDER_DETAIL_REQUESTED):
            await self._sender.send_tts_response(session_id, ORDER_DETAIL_LOADING_TTS)
            return True

        if is_order_detail_question(text):
            self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUEST_TYPE, REQUEST_QUESTION)
            self._session.set_context(session_id, CTX_ORDER_DETAIL_PENDING_QUESTION, text)
            self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUESTED, True)
            await self._sender.send_tool_calls(
                session_id,
                [
                    MCPCommand(
                        tool_name="extract_order_detail",
                        arguments={},
                        description="extract order detail",
                    )
                ],
            )
            return True

        if is_order_detail_read_request(text):
            self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUEST_TYPE, REQUEST_SUMMARY)
            self._session.set_context(session_id, CTX_ORDER_DETAIL_PENDING_QUESTION, None)
            self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUESTED, True)
            await self._sender.send_tool_calls(
                session_id,
                [
                    MCPCommand(
                        tool_name="extract_order_detail",
                        arguments={},
                        description="extract order detail",
                    )
                ],
            )
            return True

        return False

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]) -> bool:
        if not self._sender or not self._session:
            return False
        tool_name = data.get("tool_name")
        if tool_name != "extract_order_detail":
            return False

        result = data.get("result") or {}
        page_url = resolve_page_url(self._session, session_id, data)
        if not is_order_detail_url(page_url):
            return False

        if not self._session.get_context(session_id, CTX_ORDER_DETAIL_REQUESTED):
            return False
        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUESTED, False)

        order_data = result.get("order_detail") if isinstance(result, dict) else None
        if not isinstance(order_data, dict):
            order_data = {}

        # Do not store order_id in order detail data to avoid reading it out.
        self._session.set_context(session_id, CTX_ORDER_DETAIL_DATA, order_data)
        self._file_manager.save_json(
            data={
                "order_detail": order_data,
                "page_url": page_url,
            },
            session_id=session_id,
            category="order_detail",
            filename_prefix="order_detail",
        )
        order_id = extract_order_id_from_order_detail_url(page_url)
        logger.info(
            "Order detail extracted: session=%s order_id=%s items=%s",
            session_id,
            order_id or "missing",
            str(len(order_data.get("items", []))) if isinstance(order_data, dict) else "0",
        )
        if order_id:
            sent = self._session.get_context(session_id, CTX_ORDER_DETAIL_API_SENT_ID)
            if sent != order_id:
                asyncio.create_task(self._api_sender.send_order(session_id, order_id, order_data))

        request_type = self._session.get_context(session_id, CTX_ORDER_DETAIL_REQUEST_TYPE, REQUEST_SUMMARY)
        if request_type == REQUEST_QUESTION:
            question = self._session.get_context(session_id, CTX_ORDER_DETAIL_PENDING_QUESTION) or ""
            answer = await self._ask_order_detail_llm(question, order_data, page_url)
            await self._sender.send_tts_response(session_id, answer)
            return True

        summary = build_order_detail_summary(order_data)
        payment_tts = build_order_detail_payment_tts(order_data)
        actions = build_order_detail_actions(order_data)
        await self._sender.send_tts_response(session_id, summary)
        if payment_tts:
            await self._sender.send_tts_response(session_id, payment_tts)
        await self._sender.send_tts_response(session_id, actions)
        await self._sender.send_tts_response(session_id, ORDER_DETAIL_PROMPT)
        return True

    def cleanup_session(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_ORDER_DETAIL_LAST_URL, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUEST_TYPE, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_PENDING_QUESTION, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_REQUESTED, None)
        self._session.set_context(session_id, CTX_ORDER_DETAIL_DATA, None)
        self._api_sender.cleanup_session(session_id)
        self._file_manager.cleanup_session(session_id)

    async def _ask_order_detail_llm(self, question: str, order_data: Dict[str, Any], page_url: str) -> str:
        if not question:
            return ORDER_DETAIL_NOT_FOUND_TTS
        data_text = json.dumps(prune_data(order_data), ensure_ascii=False)
        data_text = truncate_text(data_text, 12000)
        system_prompt = (
            "당신은 한국어 쇼핑 도우미입니다. 아래 ORDER_DETAIL_DATA만 근거로 "
            "사용자의 질문에 간결하게 답하세요. 정보가 없으면 "
            "'주문 상세 페이지에서 해당 정보를 찾지 못했어요.'라고 말하세요. "
            "반드시 JSON 객체로만 답하세요. 형식: {\"response\": \"...\", \"commands\": []}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"ORDER_DETAIL_DATA:\n{data_text}"},
            {"role": "user", "content": question},
        ]
        result = await self._llm.generate_with_messages(messages, page_url)
        return result.response_text or ORDER_DETAIL_NOT_FOUND_TTS


__all__ = [
    "OrderDetailHandler",
    "ORDER_DETAIL_PROMPT",
    "ORDER_DETAIL_LOADING_TTS",
    "ORDER_DETAIL_NOT_FOUND_TTS",
    "CTX_ORDER_DETAIL_DATA",
]
