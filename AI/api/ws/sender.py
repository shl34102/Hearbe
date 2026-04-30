# -*- coding: utf-8 -*-
"""
WebSocket sender helpers

Centralizes outbound message formats for WS responses.
"""

import logging
import re
import uuid
from typing import Optional, Iterable, List

from core.interfaces import ASRResult
from .models import MessageType, WSMessage
from .tts.tts_normalizer import normalize_tts_text

logger = logging.getLogger(__name__)


class WSSender:
    """WS message sender with optional TTS streaming support."""

    def __init__(self, connection_manager, tts_service=None):
        self._connections = connection_manager
        self._tts = tts_service
        self._tts_epoch = {}

    async def cancel_tts(self, session_id: str):
        """Cancel ongoing TTS streaming for a session."""
        self._tts_epoch[session_id] = self._tts_epoch.get(session_id, 0) + 1

    async def send_status(self, session_id: str, status: str, message: str):
        msg = WSMessage(
            type=MessageType.STATUS,
            data={"status": status, "message": message},
            session_id=session_id
        )
        await self._connections.send_message(session_id, msg)

    async def send_error(self, session_id: str, error: str):
        msg = WSMessage(
            type=MessageType.ERROR,
            data={"error": error},
            session_id=session_id
        )
        await self._connections.send_message(session_id, msg)

    async def send_asr_result(self, session_id: str, result: ASRResult):
        msg = WSMessage(
            type=MessageType.ASR_RESULT,
            data={
                "text": result.text,
                "confidence": result.confidence,
                "language": result.language,
                "duration": result.duration,
                "is_final": result.is_final,
                "segment_id": result.segment_id
            },
            session_id=session_id
        )
        await self._connections.send_message(session_id, msg)

    async def send_tool_calls(self, session_id: str, commands: list):
        msg = WSMessage(
            type=MessageType.TOOL_CALLS,
            data={
                "commands": [
                    {
                        "tool_name": cmd.tool_name,
                        "arguments": cmd.arguments,
                        "description": cmd.description
                    }
                    for cmd in commands
                ]
            },
            session_id=session_id
        )
        logger.info(f"Sending {len(commands)} tool calls to session {session_id}")
        await self._connections.send_message(session_id, msg)

    async def send_flow_step(self, session_id: str, step):
        msg = WSMessage(
            type=MessageType.FLOW_STEP,
            data={
                "step_id": step.step_id,
                "prompt": step.prompt,
                "required_fields": step.required_fields,
                "action": step.action
            },
            session_id=session_id
        )
        await self._connections.send_message(session_id, msg)

    async def send_tts_response(self, session_id: str, text: str):
        if not self._tts:
            logger.warning("TTS service not available")
            return
        if not self._connections.is_connected(session_id):
            logger.info("Skip TTS (not connected): session=%s", session_id)
            return

        try:
            logger.info("[TTS OUTPUT] %s", text.strip() if text else "")
            tts_id = uuid.uuid4().hex[:10]
            text = _strip_urls(text)
            text = _normalize_line_breaks(text)
            text = normalize_tts_text(text)
            segments = _split_tts_text(text)
            epoch = self._tts_epoch.get(session_id, 0)
            preview = _log_preview(text, 200)
            logger.info(
                "TTS start: id=%s session=%s chars=%d segments=%d text='%s'",
                tts_id,
                session_id,
                len(text or ""),
                len(segments),
                preview,
            )
            chunk_count = 0
            disconnected = False
            for segment_index, segment in enumerate(segments):
                if self._tts_epoch.get(session_id, 0) != epoch:
                    logger.info(f"TTS cancelled: session={session_id}")
                    break
                if not self._connections.is_connected(session_id):
                    disconnected = True
                    break
                if not segment:
                    continue
                logger.info(
                    "TTS text: id=%s session=%s segment=%d/%d '%s'",
                    tts_id,
                    session_id,
                    segment_index + 1,
                    len(segments),
                    _log_preview(segment, 400),
                )
                first_chunk = True
                async for chunk in self._tts.synthesize_stream(segment):
                    if self._tts_epoch.get(session_id, 0) != epoch:
                        logger.info(f"TTS cancelled: session={session_id}")
                        break
                    if not self._connections.is_connected(session_id):
                        disconnected = True
                        break
                    data = {
                        "audio": chunk.audio_data.hex() if chunk.audio_data else "",
                        "is_final": chunk.is_final,
                        "sample_rate": chunk.sample_rate,
                        "tts_id": tts_id,
                    }
                    if first_chunk:
                        data.update(
                            {
                                "text": segment,
                                "segment_index": segment_index,
                                "segment_total": len(segments),
                            }
                        )
                        first_chunk = False
                    msg = WSMessage(
                        type=MessageType.TTS_CHUNK,
                        data=data,
                        session_id=session_id
                    )
                    ok = await self._connections.send_message(session_id, msg)
                    if not ok:
                        disconnected = True
                        break
                    chunk_count += 1
                if disconnected:
                    break
            if disconnected:
                logger.info("TTS aborted (disconnected): id=%s session=%s", tts_id, session_id)
            logger.info(
                "TTS completed: id=%s session=%s chunks=%d segments=%d",
                tts_id,
                session_id,
                chunk_count,
                len(segments),
            )
        except Exception as e:
            logger.error(f"TTS streaming failed: {e}")

    async def send_ocr_progress(
        self,
        session_id: str,
        status: str,
        progress: int,
        total_images: int,
        current_chunk: int = 0,
        total_chunks: int = 0,
        error: Optional[str] = None
    ):
        msg = WSMessage(
            type=MessageType.OCR_PROGRESS,
            data={
                "status": status,
                "progress": progress,
                "total_images": total_images,
                "current_chunk": current_chunk,
                "total_chunks": total_chunks,
                "error": error
            },
            session_id=session_id
        )
        await self._connections.send_message(session_id, msg)


_URL_PATTERN = re.compile(r"https?://\S+")


def _strip_urls(text: str) -> str:
    if not text:
        return text
    cleaned = _URL_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _normalize_line_breaks(text: str) -> str:
    if not text:
        return text
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    normalized: List[str] = []
    for line in lines:
        if re.search(r"[.!?。…]$", line):
            normalized.append(line)
        else:
            normalized.append(f"{line}.")
    return " ".join(normalized)


def _split_tts_text(text: str, max_chars: int = 200) -> List[str]:
    if not text:
        return []
    # Split by sentence endings or newlines.
    parts = re.split(r"(?<=[.!?。…])\s+|\n+", text)
    segments: List[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_chars:
            segments.append(part)
            continue
        # Further split long segments by commas or spaces.
        while len(part) > max_chars:
            cut = part.rfind(",", 0, max_chars)
            if cut == -1:
                cut = part.rfind(" ", 0, max_chars)
            if cut == -1:
                cut = max_chars
            segments.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            segments.append(part)
    return segments


def _log_preview(text: str, max_chars: int) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    if max_chars <= 0:
        return cleaned
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars] + "…"
