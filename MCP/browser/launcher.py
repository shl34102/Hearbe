"""
Chrome 브라우저 실행 모듈

CDP(Chrome DevTools Protocol) 모드로 Chrome 자동 실행
"""

import asyncio
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
import aiohttp

from core.config import get_config
from core.event_bus import EventType, publish
from browser.chrome_utils import find_chrome_path

logger = logging.getLogger(__name__)


class ChromeLauncher:
    """
    Chrome 브라우저 실행 관리자

    CDP 모드로 Chrome을 실행하고 WebSocket URL을 획득
    """

    def __init__(self):
        self._config = get_config().browser
        self._process: Optional[subprocess.Popen] = None
        self._cdp_url: Optional[str] = None
        self._actual_user_data_dir: Optional[Path] = None  # 실제 사용되는 프로필 경로

    @property
    def is_running(self) -> bool:
        """브라우저 실행 중인지 확인"""
        return self._process is not None and self._process.poll() is None

    @property
    def cdp_url(self) -> Optional[str]:
        """CDP WebSocket URL"""
        return self._cdp_url

    @property
    def process_id(self) -> Optional[int]:
        """브라우저 프로세스 ID"""
        return self._process.pid if self._process else None

    def _find_chrome_path(self) -> Optional[str]:
        """Chrome 실행 파일 경로 탐색"""
        chrome_path = find_chrome_path(self._config.chrome_path)
        if chrome_path:
            logger.info(f"Found Chrome at: {chrome_path}")
        else:
            logger.warning(f"Configured Chrome path not found: {self._config.chrome_path}")
        return chrome_path

    def _build_chrome_args(self, chrome_path: str, user_data_dir: Path) -> list:
        """Chrome 실행 인자 생성"""
        args = [
            chrome_path,
            f"--remote-debugging-port={self._config.debugging_port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--window-size={self._config.window_width},{self._config.window_height}",
        ]

        if self._config.headless:
            args.append("--headless=new")

        # Chrome Extension 자동 로드
        if self._config.extension_path:
            extension_path = Path(self._config.extension_path).resolve()
            if extension_path.exists() and extension_path.is_dir():
                args.append(f"--load-extension={extension_path}")
                logger.info(f"Loading Chrome extension from: {extension_path}")
            else:
                logger.warning(f"Extension path not found or not a directory: {extension_path}")

        # Navigate to home URL on startup
        if self._config.home_url:
            args.append(self._config.home_url)
            logger.info(f"Chrome will open to: {self._config.home_url}")

        return args

    async def start(self) -> bool:
        """
        Chrome 브라우저 시작

        Returns:
            bool: 시작 성공 여부
        """
        if self.is_running:
            logger.warning("Chrome is already running")
            return False

        # 먼저 기존 CDP 연결이 있는지 확인
        existing_cdp_url = await self._check_existing_cdp()
        if existing_cdp_url:
            logger.info(f"Found existing Chrome CDP at port {self._config.debugging_port}")
            self._cdp_url = existing_cdp_url
            
            # 브라우저 준비 완료 이벤트
            await publish(
                EventType.BROWSER_READY,
                data={
                    "cdp_url": self._cdp_url,
                    "process_id": None  # 외부에서 시작된 프로세스
                },
                source="browser.launcher"
            )
            
            logger.info(f"Connected to existing Chrome - CDP URL: {self._cdp_url}")
            return True

        # 기존 CDP가 없으면 새 Chrome 실행
        # Chrome 경로 탐색
        chrome_path = self._find_chrome_path()
        if not chrome_path:
            logger.error("Chrome executable not found")
            await publish(
                EventType.BROWSER_ERROR,
                data={"error": "Chrome executable not found"},
                source="browser.launcher"
            )
            return False

        # 사용 가능한 프로필 디렉토리 찾기 (잠겨있으면 _1, _2 등 번호 붙여서 새로 생성)
        # Chrome은 절대 경로를 요구하므로 resolve() 사용
        base_user_data_dir = Path(self._config.user_data_dir).resolve()
        user_data_dir = await self._find_available_profile_dir(base_user_data_dir)
        self._actual_user_data_dir = user_data_dir
        logger.info(f"Using profile directory: {user_data_dir}")

        # Chrome 실행
        args = self._build_chrome_args(chrome_path, user_data_dir)
        logger.info(f"Starting Chrome with args: {' '.join(args)}")

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            logger.info(f"Chrome started with PID: {self._process.pid}")

        except Exception as e:
            logger.error(f"Failed to start Chrome: {e}")
            await publish(
                EventType.BROWSER_ERROR,
                data={"error": str(e)},
                source="browser.launcher"
            )
            return False

        # CDP 연결 대기
        cdp_url = await self._wait_for_cdp()
        if not cdp_url:
            logger.error("Failed to get CDP URL")
            await self.stop()
            return False

        self._cdp_url = cdp_url

        # 브라우저 준비 완료 이벤트
        await publish(
            EventType.BROWSER_READY,
            data={
                "cdp_url": self._cdp_url,
                "process_id": self._process.pid
            },
            source="browser.launcher"
        )

        logger.info(f"Chrome ready - CDP URL: {self._cdp_url}")
        return True

    async def _check_existing_cdp(self) -> Optional[str]:
        """
        기존 CDP 연결 확인
        
        Returns:
            기존 CDP WebSocket URL 또는 None
        """
        cdp_http_url = f"http://127.0.0.1:{self._config.debugging_port}/json/version"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(cdp_http_url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("webSocketDebuggerUrl")
        except Exception:
            pass
        
        return None

    async def _wait_for_cdp(self, timeout: int = 10) -> Optional[str]:
        """
        CDP 연결 대기

        Args:
            timeout: 대기 시간 (초)

        Returns:
            CDP WebSocket URL 또는 None
        """
        cdp_http_url = f"http://127.0.0.1:{self._config.debugging_port}/json/version"

        for _ in range(timeout * 2):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(cdp_http_url, timeout=aiohttp.ClientTimeout(total=1)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get("webSocketDebuggerUrl")
            except Exception:
                pass

            await asyncio.sleep(0.5)

        return None

    async def stop(self):
        """Chrome 브라우저 종료"""
        if not self._process:
            return

        logger.info("Stopping Chrome...")

        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Chrome did not terminate gracefully, killing...")
            self._process.kill()
        except Exception as e:
            logger.error(f"Error stopping Chrome: {e}")

        self._process = None
        self._cdp_url = None
        logger.info("Chrome stopped")

    async def _find_available_profile_dir(self, base_dir: Path) -> Path:
        """
        사용 가능한 프로필 디렉토리 찾기
        
        기본 디렉토리가 잠겨있으면 _1, _2 등 번호를 붙여서 대체 디렉토리 사용
        
        Args:
            base_dir: 기본 프로필 디렉토리 경로
            
        Returns:
            Path: 사용 가능한 프로필 디렉토리 경로
        """
        # 먼저 기본 디렉토리 시도
        if await self._is_profile_available(base_dir):
            base_dir.mkdir(parents=True, exist_ok=True)
            return base_dir
        
        logger.warning(f"Profile directory is locked: {base_dir}")
        
        # 잠겨있으면 _1, _2, ... 번호 붙여서 찾기
        for i in range(1, 100):
            alt_dir = base_dir.parent / f"{base_dir.name}_{i}"
            if await self._is_profile_available(alt_dir):
                alt_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Using alternative profile: {alt_dir}")
                return alt_dir
        
        # 100개까지 다 잠겨있으면 (거의 불가능) 그냥 기본 디렉토리 반환
        logger.error("Could not find available profile directory")
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    async def _is_profile_available(self, profile_dir: Path) -> bool:
        """
        프로필 디렉토리 사용 가능 여부 확인
        
        Args:
            profile_dir: 확인할 프로필 디렉토리
            
        Returns:
            bool: 사용 가능 여부
        """
        # 디렉토리가 없으면 사용 가능
        if not profile_dir.exists():
            return True
        
        # 잠금 파일 목록
        lock_files = [
            profile_dir / "lockfile",
            profile_dir / "SingletonLock",
            profile_dir / "SingletonCookie", 
            profile_dir / "SingletonSocket",
        ]
        
        # 잠금 파일이 하나라도 있으면 사용 불가
        for lock_file in lock_files:
            if lock_file.exists():
                # 잠금 파일 삭제 시도
                try:
                    lock_file.unlink()
                    logger.info(f"Removed lock file: {lock_file.name}")
                except (PermissionError, OSError):
                    logger.warning(f"Profile locked by: {lock_file.name}")
                    return False
        
        return True

    async def clean_profile(self):
        """
        프로필 디렉토리 완전 삭제 (수동 정리용)
        """
        user_data_dir = Path(self._config.user_data_dir)
        if user_data_dir.exists():
            try:
                shutil.rmtree(user_data_dir, ignore_errors=True)
                logger.info(f"Cleaned profile directory: {user_data_dir}")
            except Exception as e:
                logger.error(f"Failed to clean profile: {e}")


