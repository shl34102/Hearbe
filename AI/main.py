"""
AI 서버 메인 진입점

시각장애인 음성 쇼핑 지원 AI 서버
"""

import asyncio
import logging
import signal
import sys
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_config, setup_logging
from core.event_bus import event_bus, EventType, publish

from services.asr import ASRService
from services.nlu import NLUService
from services.llm import LLMPlanner
from services.tts import TTSService
from services.ocr import OCRService
from services.flow import FlowEngine
from services.session import SessionManager

from api.http import router as http_router
from api.websocket import WebSocketHandler, connection_manager

logger = logging.getLogger(__name__)


class AIServer:
    """AI 서버 애플리케이션"""

    def __init__(self):
        self.config = get_config()
        setup_logging(self.config)

        # 서비스 인스턴스
        self.asr_service: ASRService = None
        self.nlu_service: NLUService = None
        self.llm_planner: LLMPlanner = None
        self.tts_service: TTSService = None
        self.ocr_service: OCRService = None
        self.flow_engine: FlowEngine = None
        self.session_manager: SessionManager = None

        # WebSocket 핸들러
        self.ws_handler: WebSocketHandler = None

        # FastAPI 앱
        self.app: FastAPI = None

        logger.info("AIServer instance created")

    async def initialize_services(self):
        """모든 서비스 초기화"""
        logger.info("Initializing services...")

        # 서비스 인스턴스 생성
        self.session_manager = SessionManager()
        self.asr_service = ASRService()
        self.nlu_service = NLUService()
        self.llm_planner = LLMPlanner()
        self.tts_service = TTSService()
        self.ocr_service = OCRService()
        self.flow_engine = FlowEngine()

        # 서비스 초기화
        await self.session_manager.initialize()
        await self.nlu_service.initialize()
        await self.llm_planner.initialize()
        await self.flow_engine.initialize()

        # ASR, TTS, OCR은 무거운 모델이므로 별도 초기화 (선택적)
        try:
            await self.asr_service.initialize()
        except Exception as e:
            logger.warning(f"ASR service initialization skipped: {e}")

        try:
            await self.tts_service.initialize()
        except Exception as e:
            logger.warning(f"TTS service initialization skipped: {e}")

        try:
            await self.ocr_service.initialize()
        except Exception as e:
            logger.warning(f"OCR service initialization skipped: {e}")

        # WebSocket 핸들러 생성
        self.ws_handler = WebSocketHandler(
            asr_service=self.asr_service,
            nlu_service=self.nlu_service,
            llm_planner=self.llm_planner,
            tts_service=self.tts_service,
            flow_engine=self.flow_engine,
            session_manager=self.session_manager
        )

        logger.info("All services initialized")

    async def _warmup_ocr(self):
        """OCR 모델을 백그라운드에서 미리 로드"""
        try:
            from services.summarizer import get_ocr_integrator
            integrator = get_ocr_integrator()
            await integrator.warmup()
        except Exception as e:
            logger.warning(f"OCR warmup skipped: {e}")

    async def shutdown_services(self):
        """모든 서비스 종료"""
        logger.info("Shutting down services...")

        if self.asr_service:
            await self.asr_service.shutdown()
        if self.nlu_service:
            await self.nlu_service.shutdown()
        if self.llm_planner:
            await self.llm_planner.shutdown()
        if self.tts_service:
            await self.tts_service.shutdown()
        if self.ocr_service:
            await self.ocr_service.shutdown()
        if self.flow_engine:
            await self.flow_engine.shutdown()
        if self.session_manager:
            await self.session_manager.shutdown()

        try:
            from api.ws.utils.temp_file_manager import TempFileManager
            TempFileManager().cleanup_all()
        except Exception as e:
            logger.warning(f"Temp cleanup skipped: {e}")

        logger.info("All services shut down")

    def create_app(self) -> FastAPI:
        """FastAPI 앱 생성"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await event_bus.start()
            try:
                from api.ws.utils.temp_file_manager import TempFileManager
                TempFileManager().cleanup_all()
            except Exception as e:
                logger.warning(f"Temp cleanup on startup skipped: {e}")
            await self.initialize_services()

            # Expose services to app state for HTTP routes
            app.state.asr_service = self.asr_service
            app.state.tts_service = self.tts_service
            app.state.ocr_service = self.ocr_service

            await publish(EventType.SERVER_STARTED, source="main")
            logger.info("AI Server started")

            # OCR 모델 백그라운드 사전 로딩
            asyncio.create_task(self._warmup_ocr())

            yield

            # Shutdown
            await publish(EventType.SERVER_SHUTDOWN, source="main")
            await self.shutdown_services()
            await event_bus.stop()
            logger.info("AI Server stopped")

        self.app = FastAPI(
            title="AI Shopping Assistant Server",
            description="시각장애인 음성 쇼핑 지원 AI 서버",
            version="1.0.0",
            lifespan=lifespan,
            debug=self.config.server.debug
        )

        origins = [
            origin.strip()
            for origin in self.config.server.cors_origins.split(",")
            if origin.strip()
        ] or ["*"]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # HTTP 라우터 등록
        self.app.include_router(http_router, prefix="/api/v1")

        # WebSocket 엔드포인트
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            # 세션 ID 생성 또는 쿼리에서 가져오기
            session_id = websocket.query_params.get("session_id", str(uuid.uuid4()))
            await self.ws_handler.handle_connection(websocket, session_id)

        @self.app.websocket("/ws/{session_id}")
        async def websocket_endpoint_with_session(websocket: WebSocket, session_id: str):
            await self.ws_handler.handle_connection(websocket, session_id)

        # 루트 엔드포인트 (healthcheck용)
        _health_check_count = {"value": 0}  # mutable for closure

        @self.app.get("/")
        async def root():
            # 3번에 1번 (약 1분 30초마다) 생존 로그 → 로그 로테이션 트리거 보장
            _health_check_count["value"] += 1
            if _health_check_count["value"] % 3 == 0:
                logger.info("Server heartbeat")

            ws_url = self.config.server.public_ws_url
            if not ws_url:
                base_url = self.config.server.public_base_url
                if base_url:
                    if base_url.startswith("https://"):
                        ws_url = "wss://" + base_url[len("https://"):]
                    elif base_url.startswith("http://"):
                        ws_url = "ws://" + base_url[len("http://"):]
                    else:
                        ws_url = base_url
                    ws_url = ws_url.rstrip("/") + self.config.server.ws_path
                else:
                    ws_url = f"ws://localhost:{self.config.server.port}{self.config.server.ws_path}"
            return {
                "name": "AI Shopping Assistant Server",
                "version": "1.0.0",
                "status": "running",
                "websocket": ws_url
            }

        return self.app

    def run(self):
        """서버 실행"""
        app = self.create_app()

        # 시그널 핸들러
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Uvicorn 실행
        uvicorn.run(
            app,
            host=self.config.server.host,
            port=self.config.server.port,
            log_level="info" if not self.config.server.debug else "debug"
        )


def main():
    """메인 함수"""
    server = AIServer()
    server.run()


# Module-level app for uvicorn (e.g., uvicorn main:app)
_server = AIServer()
app = _server.create_app()


if __name__ == "__main__":
    main()
