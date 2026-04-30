# -*- coding: utf-8 -*-
"""
WebSocket message models

Defines message types and wire formats for WS communication.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessageType(str, Enum):
    """WebSocket message types"""
    # Client -> Server
    AUDIO_CHUNK = "audio_chunk"
    USER_INPUT = "user_input"
    USER_CONFIRM = "user_confirm"
    CANCEL = "cancel"
    INTERRUPT = "interrupt"
    MCP_RESULT = "mcp_result"
    PAGE_UPDATE = "page_update"

    # Server -> Client
    ASR_RESULT = "asr_result"
    TOOL_CALLS = "tool_calls"
    FLOW_STEP = "flow_step"
    TTS_CHUNK = "tts_chunk"
    STATUS = "status"
    ERROR = "error"
    OCR_PROGRESS = "ocr_progress"  # OCR 처리 진행 상황


@dataclass
class WSMessage:
    """WebSocket message"""
    type: MessageType
    data: Any
    session_id: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


@dataclass
class AudioChunk:
    """Audio chunk with metadata"""
    data: bytes
    seq: int
    is_final: bool = False
    timestamp_ms: int = 0
