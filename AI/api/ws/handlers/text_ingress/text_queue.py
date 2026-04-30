# -*- coding: utf-8 -*-
"""
Text queue manager: per-session queue + interrupt clearing.
"""

import asyncio
import logging
from typing import Dict, Optional

from .text_normalizer import normalize_text

logger = logging.getLogger(__name__)

MAX_TEXT_QUEUE_SIZE = 20  # Max pending text messages per session


class TextQueueManager:
    def __init__(
        self,
        max_queue_size: int = MAX_TEXT_QUEUE_SIZE,
    ):
        self._max_queue_size = max_queue_size

        self._queues: Dict[str, asyncio.Queue] = {}

    def create_session(self, session_id: str) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._queues[session_id] = queue
        return queue

    def get_queue(self, session_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(session_id)

    def cleanup_session(self, session_id: str) -> None:
        self._queues.pop(session_id, None)

    def interrupt(self, session_id: str) -> None:
        queue = self._queues.get(session_id)
        if queue:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    def enqueue_text(self, session_id: str, text: str) -> bool:
        queue = self._queues.get(session_id)
        if not queue:
            logger.warning(f"No text queue for session: {session_id}")
            return False

        normalized = normalize_text(text)
        if not normalized:
            return False

        try:
            queue.put_nowait(text)
            return True
        except asyncio.QueueFull:
            logger.warning(f"Text queue full, dropping oldest: {session_id}")
            try:
                queue.get_nowait()
                queue.put_nowait(text)
                return True
            except asyncio.QueueEmpty:
                return False

    def mark_dequeued(self, session_id: str, text: str) -> None:
        pass
