"""
설정 관리 모듈

환경 변수 및 설정 파일 로드
"""

import os
import sys
import logging
import logging.handlers
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class ASRConfig:
    """ASR (음성 인식) 설정"""
    # 공통 설정
    provider: str = "whisper"  # "whisper" | "qwen3"
    device: str = "cuda"
    language: str = "ko"

    # Whisper 전용 설정
    model_name: str = "large-v3-turbo"
    compute_type: str = "float16"
    beam_size: int = 5

    # Qwen3 전용 설정
    qwen3_model_name: str = "Qwen/Qwen3-ASR-0.6B"
    qwen3_max_batch_size: int = 32
    qwen3_max_new_tokens: int = 256


@dataclass
class NLUConfig:
    """NLU (자연어 이해) 설정"""
    intent_model: str = "gpt-4o-mini"
    ner_enabled: bool = True
    context_window: int = 10


@dataclass
class LLMConfig:
    """LLM Planner 설정"""
    model_name: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # OpenAI compatible API endpoint
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class TTSConfig:
    """TTS (음성 합성) 설정 - Google Cloud TTS"""
    sample_rate: int = 24000
    streaming: bool = True
    speaking_rate: float = 1.0
    google_credentials_path: Optional[str] = None
    google_voice_name: str = "ko-KR-Chirp3-HD-Leda"  # Chirp 3 HD 한국어 음성


@dataclass
class OCRConfig:
    """OCR (이미지 인식) 설정"""
    provider: str = "openai"  # openai, tesseract, paddleocr
    api_key: Optional[str] = None
    language: str = "kor+eng"
    device: str = "cpu"  # paddleocr device (gpu, gpu:0, cpu)
    http_timeout_seconds: int = 45
    http_max_upload_mb: int = 20


@dataclass
class FlowEngineConfig:
    """Flow Engine 설정"""
    flows_dir: str = "flows"
    default_site: str = "coupang"
    confirmation_required: bool = True


@dataclass
class ServerConfig:
    """서버 설정"""
    host: str = "0.0.0.0"
    port: int = 8000
    ws_path: str = "/ws"
    cors_origins: str = "*"
    debug: bool = False
    public_base_url: Optional[str] = None
    public_ws_url: Optional[str] = None


@dataclass
class LogConfig:
    """로깅 설정"""
    level: str = "INFO"
    console_level: Optional[str] = None
    file_level: Optional[str] = None
    log_dir: str = "logs"
    log_file: str = "ai_server.log"
    rotate_when: str = "midnight"
    rotate_interval: int = 1
    backup_count: int = 5
    rotate_utc: bool = False


@dataclass
class AppConfig:
    """전체 애플리케이션 설정"""
    asr: ASRConfig
    nlu: NLUConfig
    llm: LLMConfig
    tts: TTSConfig
    ocr: OCRConfig
    flow_engine: FlowEngineConfig
    server: ServerConfig
    log: LogConfig


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
        current_dir = Path(__file__).parent.parent
        env_path = current_dir / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded .env file from {env_path}")
        else:
            logger.warning(f".env file not found at {env_path}")

    def _get_env(self, key: str, default: str = "") -> str:
        """환경 변수 가져오기"""
        return os.getenv(key, default)

    def _get_env_profile(self, key: str, default: str = "") -> str:
        """APP_ENV별 기본값을 적용하고, 동일 키가 있으면 override"""
        app_env = self._get_env("APP_ENV", "dev").strip().lower()
        profile_key = f"{app_env.upper()}_{key}"

        if os.getenv(key) is not None:
            return os.getenv(key)
        if os.getenv(profile_key) is not None:
            return os.getenv(profile_key)
        return default

    def _get_env_int(self, key: str, default: int) -> int:
        """환경 변수를 정수로 가져오기"""
        try:
            return int(self._get_env(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default

    def _get_env_float(self, key: str, default: float) -> float:
        """환경 변수를 float으로 가져오기"""
        try:
            return float(self._get_env(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default

    def _get_env_bool(self, key: str, default: bool) -> bool:
        """환경 변수를 boolean으로 가져오기"""
        value = self._get_env(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _get_env_profile_int(self, key: str, default: int) -> int:
        """APP_ENV 기본값 + override 적용 (int)"""
        try:
            return int(self._get_env_profile(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default

    def _get_env_profile_float(self, key: str, default: float) -> float:
        """APP_ENV 기본값 + override 적용 (float)"""
        try:
            return float(self._get_env_profile(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default

    def _get_env_profile_bool(self, key: str, default: bool) -> bool:
        """APP_ENV 기본값 + override 적용 (bool)"""
        value = self._get_env_profile(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _create_config(self) -> AppConfig:
        """환경 변수를 기반으로 설정 생성"""
        # ASR 설정
        asr = ASRConfig(
            # 공통
            provider=self._get_env("ASR_PROVIDER", "whisper"),
            device=self._get_env("ASR_DEVICE", "cuda"),
            language=self._get_env("ASR_LANGUAGE", "ko"),
            # Whisper 전용
            model_name=self._get_env("ASR_MODEL_NAME", "large-v3-turbo"),
            compute_type=self._get_env("ASR_COMPUTE_TYPE", "float16"),
            beam_size=self._get_env_int("ASR_BEAM_SIZE", 5),
            # Qwen3 전용
            qwen3_model_name=self._get_env("ASR_QWEN3_MODEL_NAME", "Qwen/Qwen3-ASR-0.6B"),
            qwen3_max_batch_size=self._get_env_int("ASR_QWEN3_MAX_BATCH_SIZE", 32),
            qwen3_max_new_tokens=self._get_env_int("ASR_QWEN3_MAX_NEW_TOKENS", 256),
        )

        # NLU 설정
        nlu = NLUConfig(
            intent_model=self._get_env("NLU_INTENT_MODEL", "gpt-4o-mini"),
            ner_enabled=self._get_env_bool("NLU_NER_ENABLED", True),
            context_window=self._get_env_int("NLU_CONTEXT_WINDOW", 10)
        )

        # LLM 설정
        llm_key_name = self._get_env("LLM_API_KEY_NAME")
        llm_api_key = self._get_env(llm_key_name) if llm_key_name else None
        llm = LLMConfig(
            model_name=self._get_env("LLM_MODEL_NAME", "gpt-4o-mini"),
            api_key=llm_api_key or self._get_env("OPENAI_API_KEY") or self._get_env("GMS_API_KEY") or None,
            base_url=self._get_env("OPENAI_BASE_URL") or None,
            max_tokens=self._get_env_int("LLM_MAX_TOKENS", 2048),
            temperature=self._get_env_float("LLM_TEMPERATURE", 0.7),
            timeout=self._get_env_int("LLM_TIMEOUT", 30)
        )

        # TTS 설정 (Google Cloud TTS)
        tts = TTSConfig(
            sample_rate=self._get_env_int("TTS_SAMPLE_RATE", 24000),
            streaming=self._get_env_bool("TTS_STREAMING", True),
            speaking_rate=self._get_env_float("TTS_SPEAKING_RATE", 1.0),
            google_credentials_path=self._get_env("GOOGLE_APPLICATION_CREDENTIALS") or None,
            google_voice_name=self._get_env("TTS_GOOGLE_VOICE", "ko-KR-Chirp3-HD-Leda")
        )

        # OCR 설정
        ocr = OCRConfig(
            provider=self._get_env("OCR_PROVIDER", "openai"),
            api_key=self._get_env("OCR_API_KEY") or self._get_env("OPENAI_API_KEY") or None,
            language=self._get_env("OCR_LANGUAGE", "kor+eng"),
            device=self._get_env("OCR_DEVICE", "cpu"),
            http_timeout_seconds=self._get_env_int("OCR_HTTP_TIMEOUT_SECONDS", 45),
            http_max_upload_mb=max(15, self._get_env_int("OCR_HTTP_MAX_UPLOAD_MB", 20)),
        )

        # Flow Engine 설정
        flow_engine = FlowEngineConfig(
            flows_dir=self._get_env("FLOWS_DIR", "flows"),
            default_site=self._get_env("DEFAULT_SITE", "coupang"),
            confirmation_required=self._get_env_bool("FLOW_CONFIRMATION_REQUIRED", True)
        )

        # Server 설정
        server = ServerConfig(
            host=self._get_env("SERVER_HOST", "0.0.0.0"),
            port=self._get_env_int("SERVER_PORT", 8000),
            ws_path=self._get_env("WS_PATH", "/ws"),
            cors_origins=self._get_env("CORS_ORIGINS", "*"),
            debug=self._get_env_profile_bool("DEBUG", False),
            public_base_url=self._get_env("PUBLIC_BASE_URL") or None,
            public_ws_url=self._get_env("PUBLIC_WS_URL") or None
        )

        # Log 설정
        log = LogConfig(
            level=self._get_env_profile("LOG_LEVEL", "INFO"),
            console_level=self._get_env_profile("LOG_CONSOLE_LEVEL") or None,
            file_level=self._get_env_profile("LOG_FILE_LEVEL") or None,
            log_dir=self._get_env_profile("LOG_DIR", "logs"),
            log_file=self._get_env_profile("LOG_FILE", "ai_server.log"),
            rotate_when=self._get_env_profile("LOG_ROTATE_WHEN", "midnight"),
            rotate_interval=self._get_env_profile_int("LOG_ROTATE_INTERVAL", 1),
            backup_count=self._get_env_profile_int("LOG_BACKUP_COUNT", 5),
            rotate_utc=self._get_env_profile_bool("LOG_ROTATE_UTC", False)
        )

        return AppConfig(
            asr=asr,
            nlu=nlu,
            llm=llm,
            tts=tts,
            ocr=ocr,
            flow_engine=flow_engine,
            server=server,
            log=log
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
    log_dir = Path(config.log.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / config.log.log_file

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    console_level = level_map.get(
        (config.log.console_level or config.log.level).upper(),
        logging.INFO
    )
    file_level = level_map.get(
        (config.log.file_level or config.log.level).upper(),
        logging.INFO
    )
    root_level = min(console_level, file_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    root_logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    if config.log.rotate_utc:
        formatter.converter = time.gmtime

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when=config.log.rotate_when,
        interval=config.log.rotate_interval,
        backupCount=config.log.backup_count,
        utc=config.log.rotate_utc,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(
        "Logging configured: level=%s console=%s file=%s file_path=%s rotate=%s/%s backups=%s",
        config.log.level,
        config.log.console_level or config.log.level,
        config.log.file_level or config.log.level,
        log_file,
        config.log.rotate_when,
        config.log.rotate_interval,
        config.log.backup_count
    )
