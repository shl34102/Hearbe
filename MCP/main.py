"""
MCP 데스크탑 앱 메인 진입점

시각장애인을 위한 음성 기반 웹 쇼핑 지원 애플리케이션
"""

import argparse
import os
import asyncio
import logging
import signal
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.config import get_config, setup_logging
from core.event_bus import event_bus, EventType, publish

logger = logging.getLogger(__name__)


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="MCP Desktop App - 시각장애인을 위한 음성 기반 웹 쇼핑 지원"
    )
    parser.add_argument(
        "--console", action="store_true",
        help="콘솔 입력 모드 활성화 (테스트용)"
    )
    return parser.parse_args()


class Application:
    """메인 애플리케이션 클래스"""

    def __init__(self, console_mode: bool = False):
        self.config = get_config()
        setup_logging(self.config)

        # CLI flag should override env-based config so developers can reliably
        # enable console input without editing config.env/.env.
        if console_mode:
            self.config.debug.console_enabled = True
        self.console_mode = console_mode or self.config.debug.console_enabled
        self.running = False

        # 모듈 인스턴스 (각 담당자가 구현 후 초기화)
        self.modules = {}

        logger.info("Application initialized")

    def _merge_integrated_log(self):
        """MCP 시작 시 AI+MCP 로그를 한번 통합(덮어쓰기)."""
        try:
            mcp_root = Path(__file__).parent
            shared_root = mcp_root.parent
            script_path = shared_root / "AI" / "scripts" / "merge_ai_mcp_logs.ps1"

            if not script_path.exists():
                logger.warning(f"Integrated log script not found: {script_path}")
                return

            cmd = [
                "powershell",
                "-ExecutionPolicy", "Bypass",
                "-File", str(script_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(
                    "Integrated log merge failed: rc=%s stderr=%s",
                    result.returncode,
                    (result.stderr or "").strip()
                )
                return

            logger.info("Integrated log merged (ai_mcp_integrate.log) on MCP start")
        except Exception as e:
            logger.warning(f"Integrated log merge skipped: {e}")

    async def setup_modules(self):
        """모듈 초기화"""
        logger.info("Setting up modules...")

        # UI 모듈
        from ui.ui_manager import UIManager
        self.modules["ui"] = UIManager()
        self.modules["ui"].setup_event_handlers()
        self.modules["ui"].start()

        # Browser 모듈
        from browser.launcher import ChromeLauncher
        self.modules["browser"] = ChromeLauncher()

        # MCP 모듈
        from mcp.handler import MCPHandler
        self.modules["mcp"] = MCPHandler()
        self.modules["mcp"].setup_event_handlers()

        # Network 모듈 (AI 서버 연결)
        from network.ws_client import WSClient
        self.modules["ws_client"] = WSClient()
        self.modules["ws_client"].setup_event_handlers()

        # Audio 모듈 (PTT 녹음)
        if self.console_mode:
            logger.info("Console mode enabled: audio hotkey disabled")
        else:
            try:
                from audio.audio_manager import AudioManager
                self.modules["audio"] = AudioManager(
                    hotkey=self.config.audio.hotkey,
                    input_device_index=self.config.audio.input_device_index
                )
                self.modules["audio"].setup_event_handlers()
            except ImportError as e:
                logger.warning(f"Audio module not available: {e}")
                logger.warning("Install pyaudio and keyboard for voice support")

        # Audio Player 모듈 (TTS 재생)
        try:
            from audio.player import AudioPlayer
            self.modules["audio_player"] = AudioPlayer()
            self.modules["audio_player"].start()
        except ImportError as e:
            logger.warning(f"Audio player not available: {e}")

        # 콘솔 입력 모듈 (테스트용)
        if self.console_mode:
            from debug.console_input import ConsoleInputManager
            self.modules["console_input"] = ConsoleInputManager()

        # 스크립트 입력 모듈 (테스트용)
        if os.getenv("DEBUG_SCRIPTED_INPUT", "").lower() in ("1", "true", "yes", "y", "on"):
            from debug.scripted_input import ScriptedInputManager
            self.modules["scripted_input"] = ScriptedInputManager()

        # 시스템 이벤트 핸들러
        event_bus.subscribe(EventType.APP_SHUTDOWN, self._on_shutdown)
        event_bus.subscribe(EventType.ERROR_OCCURRED, self._on_error)

        logger.info("Modules setup complete")

    async def start(self):
        """애플리케이션 시작"""
        logger.info("Starting application...")

        # MCP 실행 시 통합 로그 1회 갱신
        self._merge_integrated_log()

        await event_bus.start()
        await self.setup_modules()

        self.running = True
        await publish(EventType.APP_STARTED, source="main")

        # Browser 시작
        if "browser" in self.modules:
            await self.modules["browser"].start()

        # WebSocket 클라이언트 시작 (AI 서버 연결)
        if "ws_client" in self.modules:
            await self.modules["ws_client"].start()

        # 콘솔 입력 시작
        if "console_input" in self.modules:
            await self.modules["console_input"].start()

        # 스크립트 입력 시작
        if "scripted_input" in self.modules:
            await self.modules["scripted_input"].start()

        # Audio 모듈 시작 (PTT 녹음)
        if "audio" in self.modules:
            await self.modules["audio"].start()

        logger.info("=== MCP Desktop App is now running ===")
        if "audio" in self.modules:
            logger.info(
                "Hold %s to record voice command, release to send",
                self.config.audio.hotkey.upper()
            )
        if self.console_mode:
            logger.info("Console input mode: ON (type 'exit' to quit)")
        logger.info("Press Ctrl+C to exit")

    async def stop(self):
        """애플리케이션 종료"""
        logger.info("Stopping application...")
        self.running = False

        await publish(EventType.APP_SHUTDOWN, source="main")

        # 모듈 종료
        if "audio_player" in self.modules:
            self.modules["audio_player"].shutdown()
        if "audio" in self.modules:
            await self.modules["audio"].stop()
        if "console_input" in self.modules:
            await self.modules["console_input"].stop()
        if "scripted_input" in self.modules:
            await self.modules["scripted_input"].stop()
        if "ws_client" in self.modules:
            await self.modules["ws_client"].stop()
        if "mcp" in self.modules:
            await self.modules["mcp"].stop()
        if "browser" in self.modules:
            await self.modules["browser"].stop()
        if "ui" in self.modules:
            self.modules["ui"].stop()

        await event_bus.stop()
        logger.info("Application stopped")

    async def run(self):
        """메인 실행 루프"""
        try:
            await self.start()
            while self.running:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            await self.stop()

    async def _on_shutdown(self, _event):
        """종료 이벤트 처리"""
        self.running = False

    async def _on_error(self, event):
        """에러 이벤트 처리"""
        logger.error(f"Error: {event.data}")


def main():
    """메인 함수"""
    args = parse_args()

    print("=" * 60)
    print("MCP Desktop App")
    print("=" * 60)

    app = Application(console_mode=args.console)

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    def signal_handler(signum, frame):
        app.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        loop.run_until_complete(app.run())
    finally:
        loop.close()

    print("Goodbye!")


if __name__ == "__main__":
    main()
