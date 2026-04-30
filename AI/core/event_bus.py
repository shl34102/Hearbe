"""
중앙 이벤트 버스 (Central Event Bus)

모든 모듈 간의 통신을 중재하는 이벤트 기반 아키텍처의 핵심
비동기 이벤트 발행/구독 패턴 구현
"""

import asyncio
import logging
from typing import Callable, Dict, List, Any
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class EventType(Enum):
    """이벤트 타입 정의"""
    # WebSocket 이벤트
    CLIENT_CONNECTED = auto()
    CLIENT_DISCONNECTED = auto()

    # ASR (음성 인식) 이벤트
    AUDIO_CHUNK_RECEIVED = auto()
    ASR_PROCESSING_STARTED = auto()
    ASR_RESULT_READY = auto()
    ASR_ERROR = auto()

    # NLU (자연어 이해) 이벤트
    INTENT_ANALYSIS_STARTED = auto()
    INTENT_RESULT_READY = auto()
    NER_RESULT_READY = auto()
    NLU_ERROR = auto()

    # LLM Planner 이벤트
    COMMAND_GENERATION_STARTED = auto()
    COMMAND_READY = auto()
    MCP_TOOL_CALL_GENERATED = auto()
    FLOW_DELEGATION_REQUIRED = auto()
    LLM_ERROR = auto()

    # TTS (음성 합성) 이벤트
    TTS_GENERATION_STARTED = auto()
    TTS_CHUNK_READY = auto()
    TTS_COMPLETE = auto()
    TTS_ERROR = auto()

    # OCR (이미지 인식) 이벤트
    IMAGE_RECEIVED = auto()
    OCR_PROCESSING_STARTED = auto()
    OCR_RESULT_READY = auto()
    OCR_ERROR = auto()

    # Flow Engine 이벤트
    FLOW_STARTED = auto()
    FLOW_STEP_STARTED = auto()
    FLOW_STEP_COMPLETED = auto()
    FLOW_COMPLETED = auto()
    FLOW_CANCELLED = auto()
    FLOW_ERROR = auto()
    USER_CONFIRMATION_REQUIRED = auto()
    USER_INPUT_REQUIRED = auto()

    # Session 이벤트
    SESSION_CREATED = auto()
    SESSION_UPDATED = auto()
    SESSION_EXPIRED = auto()
    CONTEXT_UPDATED = auto()

    # MCP 이벤트
    MCP_RESULT_RECEIVED = auto()
    MCP_ERROR = auto()

    # 시스템 이벤트
    SERVER_STARTED = auto()
    SERVER_SHUTDOWN = auto()
    ERROR_OCCURRED = auto()


@dataclass
class Event:
    """이벤트 데이터 클래스"""
    type: EventType
    data: Any = None
    timestamp: datetime = None
    source: str = None
    session_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventBus:
    """
    이벤트 버스 (Singleton)

    모든 모듈이 공유하는 중앙 이벤트 버스
    이벤트 발행, 구독, 처리 관리
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

        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._initialized = True

        logger.info("EventBus initialized")

    def subscribe(self, event_type: EventType, callback: Callable):
        """
        이벤트 구독

        Args:
            event_type: 구독할 이벤트 타입
            callback: 이벤트 발생 시 호출할 콜백 함수
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.name}: {callback.__name__}")

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """
        이벤트 구독 해제

        Args:
            event_type: 구독 해제할 이벤트 타입
            callback: 제거할 콜백 함수
        """
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.name}: {callback.__name__}")

    async def publish(self, event: Event):
        """
        이벤트 발행

        Args:
            event: 발행할 이벤트 객체
        """
        logger.debug(f"Event published: {event.type.name} from {event.source}")
        await self._event_queue.put(event)

    def publish_sync(self, event: Event):
        """
        동기 방식으로 이벤트 발행 (비동기 컨텍스트가 아닐 때 사용)

        Args:
            event: 발행할 이벤트 객체
        """
        try:
            loop = asyncio.get_running_loop()
            asyncio.ensure_future(self.publish(event), loop=loop)
        except RuntimeError:
            asyncio.run(self.publish(event))

    async def _process_events(self):
        """이벤트 큐에서 이벤트를 처리하는 메인 루프"""
        logger.info("Event processing loop started")

        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                if event.type in self._subscribers:
                    for callback in self._subscribers[event.type]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(event)
                            else:
                                callback(event)
                        except Exception as e:
                            logger.error(
                                f"Error in event callback {callback.__name__} "
                                f"for {event.type.name}: {e}",
                                exc_info=True
                            )

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)

        logger.info("Event processing loop stopped")

    async def start(self):
        """이벤트 버스 시작"""
        if self._running:
            logger.warning("EventBus already running")
            return

        self._running = True
        asyncio.create_task(self._process_events())
        logger.info("EventBus started")

    async def stop(self):
        """이벤트 버스 종료"""
        logger.info("Stopping EventBus...")
        self._running = False

        while not self._event_queue.empty():
            try:
                await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                break

        logger.info("EventBus stopped")

    def get_subscribers_count(self, event_type: EventType) -> int:
        """특정 이벤트 타입의 구독자 수 반환"""
        return len(self._subscribers.get(event_type, []))

    def clear_subscribers(self):
        """모든 구독자 제거 (테스트용)"""
        self._subscribers.clear()
        logger.info("All subscribers cleared")


# 싱글톤 인스턴스 생성
event_bus = EventBus()


# 편의 함수들
def subscribe(event_type: EventType, callback: Callable):
    """전역 이벤트 버스에 구독"""
    event_bus.subscribe(event_type, callback)


def unsubscribe(event_type: EventType, callback: Callable):
    """전역 이벤트 버스 구독 해제"""
    event_bus.unsubscribe(event_type, callback)


async def publish(event_type: EventType, data: Any = None, source: str = None, session_id: str = None):
    """전역 이벤트 버스에 이벤트 발행"""
    event = Event(type=event_type, data=data, source=source, session_id=session_id)
    await event_bus.publish(event)


def publish_sync(event_type: EventType, data: Any = None, source: str = None, session_id: str = None):
    """동기 방식으로 전역 이벤트 버스에 이벤트 발행"""
    event = Event(type=event_type, data=data, source=source, session_id=session_id)
    event_bus.publish_sync(event)
