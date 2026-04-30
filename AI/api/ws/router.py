# -*- coding: utf-8 -*-
"""
WebSocket message router

Routes incoming messages to handler manager.
"""

import json
import logging

from .models import MessageType

logger = logging.getLogger(__name__)


class WebSocketRouter:
    """Message router for WS text/binary frames."""

    def __init__(self, handler_manager):
        self._handlers = handler_manager

    async def handle_text(self, session_id: str, text: str):
        try:
            msg = json.loads(text)
            msg_type = msg.get("type")
            data = msg.get("data", {})

            logger.debug(f"Received message: type={msg_type}, session={session_id}")

            if msg_type == MessageType.AUDIO_CHUNK:
                await self._handlers.handle_audio_chunk(session_id, data)
            elif msg_type == MessageType.USER_INPUT:
                await self._handlers.handle_user_input(session_id, data)
            elif msg_type == MessageType.USER_CONFIRM:
                await self._handlers.handle_user_confirm(session_id, data)
            elif msg_type == MessageType.CANCEL:
                await self._handlers.handle_cancel(session_id)
            elif msg_type == MessageType.INTERRUPT:
                await self._handlers.handle_interrupt(session_id)
            elif msg_type == MessageType.MCP_RESULT:
                await self._handlers.handle_mcp_result(session_id, data)
            elif msg_type == MessageType.PAGE_UPDATE:
                await self._handlers.handle_page_update(session_id, data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            await self._handlers.handle_invalid_message(session_id, "Invalid message format")

    async def handle_binary(self, session_id: str, data: bytes):
        await self._handlers.handle_binary_audio(session_id, data)
