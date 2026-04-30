"""
콘솔 입력 모듈 (테스트용)

개발/디버깅 목적으로 콘솔에서 직접 텍스트를 입력하여 AI 서버로 전송.
음성 녹음 → STT 과정을 건너뛰고 바로 텍스트 명령을 테스트할 수 있음.
"""

import asyncio
import logging
import sys
from typing import Optional

from core.event_bus import EventType, publish
from core.config import get_config

logger = logging.getLogger(__name__)


class ConsoleInputManager:
    """
    콘솔 입력 관리자

    터미널에서 텍스트 입력을 받아 TEXT_INPUT_READY 이벤트로 발행
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._config = get_config()

    @property
    def is_enabled(self) -> bool:
        """콘솔 입력 모드 활성화 여부"""
        return self._config.debug.console_enabled

    @property
    def is_running(self) -> bool:
        """실행 중인지 확인"""
        return self._running

    async def start(self) -> bool:
        """
        콘솔 입력 시작

        Returns:
            bool: 시작 성공 여부
        """
        if not self.is_enabled:
            logger.info("Console input is disabled (DEBUG_CONSOLE_ENABLED=false)")
            return False

        if self._running:
            logger.warning("Console input already running")
            return False

        self._running = True
        self._task = asyncio.create_task(self._input_loop())
        logger.info("Console input started")
        print("\n[Console Input Mode] 텍스트를 입력하세요 (종료: 'exit' 또는 'quit'):")
        return True

    async def stop(self):
        """콘솔 입력 종료"""
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

        logger.info("Console input stopped")

    async def _input_loop(self):
        """입력 대기 루프"""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # 비동기로 stdin 읽기
                text = await loop.run_in_executor(None, self._read_input)

                if text is None:
                    continue

                # 종료 명령 확인
                if text.lower() in ("exit", "quit"):
                    logger.info("Exit command received")
                    break

                # 빈 입력 무시
                if not text.strip():
                    continue

                # 이벤트 발행
                await self._publish_text(text.strip())

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in console input loop: {e}")

    def _read_input(self) -> Optional[str]:
        """
        동기 방식으로 입력 읽기 (executor에서 실행)

        Returns:
            str: 입력된 텍스트 또는 None
        """
        try:
            print("> ", end="", flush=True)
            return input()
        except EOFError:
            return None
        except KeyboardInterrupt:
            return "exit"

    async def _publish_text(self, text: str):
        """
        텍스트 입력 이벤트 발행

        Args:
            text: 입력된 텍스트
        """
        logger.info(f"Text input received: {text}")
        print(f"[전송] {text}")

        await publish(
            EventType.TEXT_INPUT_READY,
            data=text,
            source="debug.console_input"
        )


# 편의 함수
async def start_console_input() -> bool:
    """콘솔 입력 시작 (편의 함수)"""
    manager = ConsoleInputManager()
    return await manager.start()
