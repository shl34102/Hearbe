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
    # Audio 모듈 이벤트
    HOTKEY_PRESSED = auto()
    RECORDING_STARTED = auto()
    RECORDING_STOPPED = auto()
    AUDIO_READY = auto()
    TTS_PLAYBACK_FINISHED = auto()
    AUDIO_DEVICE_CHANGED = auto()

    # Network 모듈 이벤트
    WS_CONNECTED = auto()
    WS_DISCONNECTED = auto()
    STT_RESULT_RECEIVED = auto()
    LLM_COMMAND_RECEIVED = auto()
    TTS_AUDIO_RECEIVED = auto()
    MCP_TOOL_CALL = auto()

    # Browser 모듈 이벤트
    BROWSER_READY = auto()
    BROWSER_ERROR = auto()
    PAGE_URL_UPDATED = auto()

    # MCP 모듈 이벤트
    MCP_SERVER_READY = auto()
    MCP_RESULT = auto()
    MCP_ERROR = auto()

    # Session 모듈 이벤트
    SESSION_UPDATED = auto()

    # Debug 모듈 이벤트
    TEXT_INPUT_READY = auto()

    # 시스템 이벤트
    APP_STARTED = auto()
    APP_SHUTDOWN = auto()
    ERROR_OCCURRED = auto()


@dataclass
class Event:
    """이벤트 데이터 클래스"""
    type: EventType
    data: Any = None
    timestamp: datetime = None
    source: str = None

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
        self._process_task = None
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
            # 이벤트 루프가 없으면 새로 생성
            asyncio.run(self.publish(event))

    async def _process_events(self):
        """이벤트 큐에서 이벤트를 처리하는 메인 루프"""
        logger.info("Event processing loop started")

        while self._running:
            try:
                # 이벤트 가져오기 (타임아웃 1초)
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                # 해당 이벤트 타입의 구독자들에게 전달
                if event.type in self._subscribers:
                    for callback in self._subscribers[event.type]:
                        try:
                            # 콜백이 코루틴이면 await, 아니면 직접 호출
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
                # 타임아웃은 정상 (큐가 비어있음)
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
        self._process_task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")

    async def stop(self):
        """이벤트 버스 종료"""
        logger.info("Stopping EventBus...")
        self._running = False

        # 프로세스 태스크 취소 및 대기
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
            self._process_task = None

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


async def publish(event_type: EventType, data: Any = None, source: str = None):
    """전역 이벤트 버스에 이벤트 발행"""
    event = Event(type=event_type, data=data, source=source)
    await event_bus.publish(event)


def publish_sync(event_type: EventType, data: Any = None, source: str = None):
    """동기 방식으로 전역 이벤트 버스에 이벤트 발행"""
    event = Event(type=event_type, data=data, source=source)
    event_bus.publish_sync(event)
