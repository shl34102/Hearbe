# -*- coding: utf-8 -*-
"""
Scripted input module (test helper).

Reads a UTF-8 text file and publishes TEXT_INPUT_READY events
at a fixed interval. Useful for automated, non-ASR tests.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from core.event_bus import EventType, publish

logger = logging.getLogger(__name__)


class ScriptedInputManager:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def is_enabled(self) -> bool:
        value = os.getenv("DEBUG_SCRIPTED_INPUT", "false").lower()
        return value in ("1", "true", "yes", "y", "on")

    def _get_input_path(self) -> Path:
        path = os.getenv("DEBUG_SCRIPTED_INPUT_FILE", "").strip()
        if path:
            return Path(path)
        return Path(__file__).parent / "scripted_input.txt"

    def _get_delay(self) -> float:
        try:
            return float(os.getenv("DEBUG_SCRIPTED_INPUT_DELAY_MS", "12000")) / 1000.0
        except ValueError:
            return 12.0

    def _get_start_delay(self) -> float:
        # Give the app a short time to connect to the AI server / browser before
        # sending the first scripted input line.
        try:
            return float(os.getenv("DEBUG_SCRIPTED_INPUT_START_DELAY_MS", "3000")) / 1000.0
        except ValueError:
            return 3.0

    async def start(self) -> bool:
        if not self.is_enabled():
            logger.info("Scripted input disabled (DEBUG_SCRIPTED_INPUT=false)")
            return False
        if self._running:
            logger.warning("Scripted input already running")
            return False

        input_path = self._get_input_path()
        if not input_path.exists():
            logger.warning("Scripted input file not found: %s", input_path)
            return False

        self._running = True
        self._task = asyncio.create_task(self._run_script(input_path))
        logger.info("Scripted input started: %s", input_path)
        return True

    async def stop(self):
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scripted input stopped")

    async def _run_script(self, input_path: Path):
        delay = self._get_delay()
        start_delay = self._get_start_delay()
        if start_delay > 0:
            logger.info("Scripted input initial delay: %.2fs", start_delay)
            await asyncio.sleep(start_delay)
            if not self._running:
                return
        try:
            lines = input_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            logger.error("Failed to read scripted input file: %s", e)
            return

        for raw in lines:
            if not self._running:
                break
            text = raw.strip()
            if not text or text.startswith("#"):
                continue
            logger.info("Scripted input send: %s", text)
            await publish(EventType.TEXT_INPUT_READY, data=text, source="debug.scripted_input")
            await asyncio.sleep(delay)
