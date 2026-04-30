# -*- coding: utf-8 -*-
"""
Audio handler: audio_chunk -> ASR -> enqueue text
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Callable

from core.event_bus import EventType, publish
from core.interfaces import ASRResult
from ..models import AudioChunk

logger = logging.getLogger(__name__)

# Audio contract constants
AUDIO_SAMPLE_RATE = 16000          # 16kHz (Whisper requirement)
AUDIO_CHANNELS = 1                 # Mono
AUDIO_BIT_DEPTH = 16               # 16-bit
AUDIO_BYTES_PER_SAMPLE = 2         # 16-bit = 2 bytes
AUDIO_FRAME_MS = 20                # 20ms frame (VAD compatible)
AUDIO_FRAME_BYTES = AUDIO_SAMPLE_RATE * AUDIO_BYTES_PER_SAMPLE * AUDIO_FRAME_MS // 1000  # 640 bytes

# Buffer thresholds
BUFFER_THRESHOLD_BYTES = 32000     # ~1 second of audio
BUFFER_OVERLAP_BYTES = 6400        # 200ms overlap for continuity
MAX_BUFFER_SIZE = 320000           # 10 seconds max (memory limit)
MAX_QUEUE_SIZE = 50                # Max pending chunks per session

# Global ASR lock for GPU serialization
_asr_lock = asyncio.Lock()


class AudioHandler:
    """Handles audio streaming and ASR pipeline."""

    def __init__(self, asr_service, sender, enqueue_text: Callable[[str, str], asyncio.Future]):
        self._asr = asr_service
        self._sender = sender
        self._enqueue_text = enqueue_text

        self._audio_queues: Dict[str, asyncio.Queue] = {}
        self._audio_buffers: Dict[str, bytes] = {}
        self._worker_tasks: Dict[str, asyncio.Task] = {}
        self._chunk_counters: Dict[str, int] = {}
        self._segment_counters: Dict[str, int] = {}

    async def create_session(self, session_id: str):
        self._audio_queues[session_id] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self._audio_buffers[session_id] = b""
        self._chunk_counters[session_id] = 0
        self._segment_counters[session_id] = 0

        self._worker_tasks[session_id] = asyncio.create_task(
            self._asr_worker(session_id)
        )

    async def cleanup_session(self, session_id: str):
        task = self._worker_tasks.pop(session_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._audio_queues.pop(session_id, None)
        self._audio_buffers.pop(session_id, None)
        self._chunk_counters.pop(session_id, None)
        self._segment_counters.pop(session_id, None)

    async def clear_audio(self, session_id: str):
        self._audio_buffers[session_id] = b""
        queue = self._audio_queues.get(session_id)
        if queue:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def handle_audio_chunk(self, session_id: str, audio_data: bytes, seq: int, is_final: bool):
        queue = self._audio_queues.get(session_id)
        if not queue:
            logger.warning(f"No queue for session: {session_id}")
            return

        chunk = AudioChunk(
            data=audio_data,
            seq=seq,
            is_final=is_final,
            timestamp_ms=int(datetime.now().timestamp() * 1000)
        )

        try:
            queue.put_nowait(chunk)
        except asyncio.QueueFull:
            logger.warning(f"Queue full, dropping chunk: {session_id}")
            try:
                queue.get_nowait()
                queue.put_nowait(chunk)
            except asyncio.QueueEmpty:
                pass

    async def handle_binary_audio(self, session_id: str, data: bytes):
        counter = self._chunk_counters.get(session_id, 0) + 1
        self._chunk_counters[session_id] = counter
        await self.handle_audio_chunk(session_id, data, counter, False)

    async def _asr_worker(self, session_id: str):
        """
        ASR worker task for PTT mode.

        Client controls recording start/stop:
        - Receives audio chunks and buffers them
        - Transcribes when is_final=true
        """
        queue = self._audio_queues.get(session_id)
        if not queue:
            return

        logger.debug(f"ASR worker started: {session_id}")

        try:
            while True:
                try:
                    chunk: AudioChunk = await asyncio.wait_for(
                        queue.get(),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    continue

                buffer = self._audio_buffers.get(session_id, b"")
                buffer += chunk.data
                self._audio_buffers[session_id] = buffer

                if len(buffer) > MAX_BUFFER_SIZE:
                    logger.warning(f"Buffer overflow, truncating: {session_id}")
                    buffer = buffer[-MAX_BUFFER_SIZE:]
                    self._audio_buffers[session_id] = buffer

                should_transcribe = chunk.is_final and len(buffer) > 0
                if should_transcribe and self._asr and self._asr.is_ready():
                    await self._process_audio_buffer(session_id, buffer, chunk.is_final)
                    self._audio_buffers[session_id] = b""

        except asyncio.CancelledError:
            logger.debug(f"ASR worker cancelled: {session_id}")
        except Exception as e:
            logger.error(f"ASR worker error: {session_id}: {e}")

    async def _process_audio_buffer(self, session_id: str, audio_data: bytes, is_final: bool):
        try:
            self._segment_counters[session_id] = self._segment_counters.get(session_id, 0) + 1
            segment_id = f"seg_{self._segment_counters[session_id]}"

            await publish(
                EventType.ASR_PROCESSING_STARTED,
                data={"segment_id": segment_id},
                session_id=session_id
            )

            async with _asr_lock:
                asr_result = await self._asr.transcribe(
                    audio_data,
                    is_final=is_final,
                    segment_id=segment_id
                )

            await self._sender.send_asr_result(session_id, asr_result)

            await publish(
                EventType.ASR_RESULT_READY,
                data={
                    "text": asr_result.text,
                    "is_final": asr_result.is_final,
                    "segment_id": asr_result.segment_id
                },
                session_id=session_id
            )

            if is_final and asr_result.text.strip():
                logger.info("[INPUT] ASR: %s", asr_result.text.strip())
                await self._enqueue_text(session_id, asr_result.text)

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            await publish(
                EventType.ASR_ERROR,
                data={"error": str(e)},
                session_id=session_id
            )
            await self._sender.send_error(session_id, "Audio processing error")
