"""
설정 관리 모듈

환경 변수 및 설정 파일 로드
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import sys

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """오디오 설정"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    hotkey: str = "space"
    input_device_index: Optional[int] = None


@dataclass
class BrowserConfig:
    """브라우저 설정"""
    chrome_path: Optional[str] = None
    user_data_dir: Optional[str] = None
    debugging_port: int = 9222
    headless: bool = False
    window_width: int = 1280
    window_height: int = 720
    extension_path: Optional[str] = None
    home_url: Optional[str] = None


@dataclass
class MCPConfig:
    """MCP 서버 설정"""
    server_script: str = "mcp/playwright_mcp_server.py"
    python_path: Optional[str] = None
    timeout: int = 30


@dataclass
class NetworkConfig:
    """네트워크 설정"""
    ws_url: str = "ws://localhost:8000/ws"
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10


@dataclass
class LogConfig:
    """로깅 설정"""
    level: str = "INFO"
    file_path: str = "./logs/app.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class SessionConfig:
    """세션 설정"""
    file_path: str = "./session.json"
    auto_save: bool = True


@dataclass
class DebugConfig:
    """디버그 설정"""
    console_enabled: bool = False


@dataclass
class AppConfig:
    """전체 애플리케이션 설정"""
    audio: AudioConfig
    browser: BrowserConfig
    mcp: MCPConfig
    network: NetworkConfig
    log: LogConfig
    session: SessionConfig
    debug: DebugConfig


class ConfigManager:
    """
    설정 관리자 (Singleton)

    환경 변수와 기본값을 결합하여 애플리케이션 설정 관리
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # .env 파일 로드
        self._load_env()

        # 설정 초기화
        self.config = self._create_config()

        self._initialized = True
        logger.info("ConfigManager initialized")

    def _load_env(self):
        """환경 변수 로드"""
        # 현재 파일의 부모 디렉토리(MCP/)에서 설정 파일 찾기
        current_dir = Path(__file__).parent.parent
        exe_dir = Path(sys.executable).parent

        # 우선순위: exe 옆 -> _internal -> 프로젝트 루트
        # config.env 우선 (Windows Defender가 .env 삭제하는 문제 방지)
        candidates = [
            exe_dir / "config.env",
            exe_dir / "_internal" / "config.env",
            exe_dir / ".env",
            exe_dir / "_internal" / ".env",
            current_dir / "config.env",
            current_dir / ".env",
        ]

        for env_path in candidates:
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded .env file from {env_path}")
                return

        logger.warning(
            ".env file not found. Checked: "
            + ", ".join(str(p) for p in candidates)
        )

    def _get_env(self, key: str, default: str = "") -> str:
        """환경 변수 가져오기"""
        return os.getenv(key, default)

    def _get_env_int(self, key: str, default: int) -> int:
        """환경 변수를 정수로 가져오기"""
        try:
            return int(self._get_env(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default

    def _get_env_int_optional(self, key: str) -> Optional[int]:
        """환경 변수를 Optional int로 가져오기"""
        value = self._get_env(key, "").strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, ignoring: {value}")
            return None

    def _get_env_bool(self, key: str, default: bool) -> bool:
        """환경 변수를 boolean으로 가져오기"""
        value = self._get_env(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _get_extension_path(self) -> Optional[str]:
        """Chrome Extension 경로 자동 탐지 (개발/배포 환경 대응)"""
        # 1. 환경변수 우선 사용
        env_path = self._get_env("CHROME_EXTENSION_PATH")
        if env_path and Path(env_path).exists():
            return env_path
        
        # 2. PyInstaller 번들 환경 (_internal/hearbe-extension)
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 실행 파일
            exe_dir = Path(sys.executable).parent
            bundled_path = exe_dir / "_internal" / "hearbe-extension"
            if bundled_path.exists():
                logger.info(f"Found bundled extension at: {bundled_path}")
                return str(bundled_path)
        
        # 3. 개발 환경 (../Frontend/hearbe-extension)
        current_dir = Path(__file__).parent.parent
        dev_path = current_dir.parent / "Frontend" / "hearbe-extension"
        if dev_path.exists():
            logger.info(f"Found development extension at: {dev_path}")
            return str(dev_path)
        
        logger.warning("Chrome extension not found in any expected location")
        return None

    def _create_config(self) -> AppConfig:
        """환경 변수를 기반으로 설정 생성"""
        # Audio 설정
        audio = AudioConfig(
            sample_rate=self._get_env_int("AUDIO_SAMPLE_RATE", 16000),
            channels=self._get_env_int("AUDIO_CHANNELS", 1),
            chunk_size=self._get_env_int("AUDIO_CHUNK_SIZE", 1024),
            hotkey=self._get_env("HOTKEY", "space"),
            input_device_index=self._get_env_int_optional("AUDIO_INPUT_DEVICE_INDEX")
        )

        # Browser 설정
        browser = BrowserConfig(
            chrome_path=self._get_env("BROWSER_EXECUTABLE_PATH") or None,
            user_data_dir=self._get_env("BROWSER_USER_DATA_DIR", "./chrome_profile"),
            debugging_port=self._get_env_int("BROWSER_CDP_PORT", 9222),
            headless=self._get_env_bool("BROWSER_HEADLESS", False),
            window_width=self._get_env_int("BROWSER_WINDOW_WIDTH", 1280),
            window_height=self._get_env_int("BROWSER_WINDOW_HEIGHT", 720),
            extension_path=self._get_extension_path(),
            home_url=self._get_env("HOME_URL", "https://i14d108.p.ssafy.io/main?app=mcp")
        )

        # MCP 설정
        mcp = MCPConfig(
            server_script=self._get_env("MCP_SERVER_COMMAND", "python mcp/playwright_mcp_server.py"),
            python_path=self._get_env("PYTHON_PATH") or None,
            timeout=self._get_env_int("MCP_SERVER_TIMEOUT", 10)
        )

        # Network 설정
        network = NetworkConfig(
            ws_url=self._get_env("WS_URL", "ws://localhost:8000/ws"),
            reconnect_interval=self._get_env_int("WS_RECONNECT_DELAY", 5),
            max_reconnect_attempts=self._get_env_int("WS_MAX_RETRIES", 10)
        )

        # Log 설정
        log = LogConfig(
            level=self._get_env("LOG_LEVEL", "INFO"),
            file_path=self._get_env("LOG_FILE_PATH", "./logs/app.log"),
            max_bytes=self._get_env_int("LOG_MAX_BYTES", 10 * 1024 * 1024),
            backup_count=self._get_env_int("LOG_BACKUP_COUNT", 5)
        )

        # Session 설정
        session = SessionConfig(
            file_path=self._get_env("SESSION_FILE_PATH", "./session.json"),
            auto_save=self._get_env_bool("SESSION_AUTO_SAVE", True)
        )

        # Debug 설정
        debug = DebugConfig(
            console_enabled=self._get_env_bool("DEBUG_CONSOLE_ENABLED", False)
        )

        # 전체 설정
        return AppConfig(
            audio=audio,
            browser=browser,
            mcp=mcp,
            network=network,
            log=log,
            session=session,
            debug=debug
        )

    def get(self) -> AppConfig:
        """현재 설정 반환"""
        return self.config

    def reload(self):
        """설정 다시 로드"""
        logger.info("Reloading configuration...")
        self._load_env()
        self.config = self._create_config()
        logger.info("Configuration reloaded")


# 싱글톤 인스턴스
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """전역 설정 가져오기"""
    return config_manager.get()


def setup_logging(config: AppConfig):
    """로깅 설정"""
    # 로그 파일 경로
    log_file = Path(config.log.file_path)

    # 로그 디렉토리 생성
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # 로그 레벨 매핑
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level = level_map.get(config.log.level.upper(), logging.INFO)

    # 로깅 설정
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # 파일 핸들러 (rotating)
            logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config.log.max_bytes,
                backupCount=config.log.backup_count,
                encoding="utf-8"
            ),
            # 콘솔 핸들러
            logging.StreamHandler()
        ]
    )

    logger.info(f"Logging configured: level={config.log.level}, file={log_file}")
