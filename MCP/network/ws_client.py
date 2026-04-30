"""
WebSocket Client Module

AI 서버와의 WebSocket 연결 및 메시지 처리
- tool_calls 메시지 수신 → MCP_TOOL_CALL 이벤트 발행
- MCP_RESULT 이벤트 구독 → mcp_result 메시지 전송
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
from asyncio import Queue

import websockets
from websockets.client import WebSocketClientProtocol

from core.config import get_config
from core.event_bus import event_bus, EventType, publish

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket 메시지 타입 (AI 서버 프로토콜과 동일)"""
    # Client → Server
    AUDIO_CHUNK = "audio_chunk"  # PTT 오디오 청크
    USER_INPUT = "user_input"
    MCP_RESULT = "mcp_result"
    INTERRUPT = "interrupt"
    PAGE_UPDATE = "page_update"
    
    # Server → Client
    ASR_RESULT = "asr_result"
    TOOL_CALLS = "tool_calls"
    FLOW_STEP = "flow_step"
    TTS_CHUNK = "tts_chunk"
    STATUS = "status"
    ERROR = "error"


class WSClient:
    """
    AI 서버 WebSocket 클라이언트
    
    AI 서버에서 도구 호출 명령을 받아 이벤트 버스로 전달하고,
    MCP 실행 결과를 AI 서버로 응답합니다.
    """
    
    def __init__(self):
        self._config = get_config().network
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._session_id: str = str(uuid.uuid4())
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        # Text inputs (console/scripted) should not be dropped during transient reconnects.
        self._text_input_queue: "Queue[str]" = Queue()
        self._text_input_sender_task: Optional[asyncio.Task] = None
        
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인
        
        Note: websocket.closed 속성은 비동기 환경에서 불안정할 수 있어
        단순히 websocket 객체 존재 여부만 확인하고, 실제 전송 시 예외 처리로 대응
        """
        if self._websocket is None:
            return False
        if hasattr(self._websocket, "open"):
            return bool(self._websocket.open)
        if hasattr(self._websocket, "closed"):
            return not bool(self._websocket.closed)
        return True
    
    @property
    def session_id(self) -> str:
        """현재 세션 ID"""
        return self._session_id
    
    def setup_event_handlers(self):
        """이벤트 핸들러 등록"""
        event_bus.subscribe(EventType.MCP_RESULT, self._on_mcp_result)
        event_bus.subscribe(EventType.AUDIO_READY, self._on_audio_ready)  # PTT 오디오
        event_bus.subscribe(EventType.HOTKEY_PRESSED, self._on_hotkey_pressed)
        event_bus.subscribe(EventType.PAGE_URL_UPDATED, self._on_page_url_updated)
        event_bus.subscribe(EventType.TEXT_INPUT_READY, self._on_text_input_ready)
        event_bus.subscribe(EventType.APP_SHUTDOWN, self._on_shutdown)
        logger.info("WSClient event handlers registered")
    
    async def connect(self) -> bool:
        """
        AI 서버에 WebSocket 연결
        
        Returns:
            연결 성공 여부
        """
        if self.is_connected:
            logger.warning("Already connected to AI server")
            return True
        
        ws_url = f"{self._config.ws_url}/{self._session_id}"
        
        try:
            self._websocket = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            self._running = True
            
            # 메시지 수신 태스크 시작
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Connected to AI server: {ws_url}")
            
            # 연결 이벤트 발행
            await publish(
                EventType.WS_CONNECTED,
                data={"session_id": self._session_id, "url": ws_url},
                source="network.ws_client"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to AI server: {e}")
            return False
    
    async def disconnect(self):
        """연결 해제"""
        self._running = False

        if self._text_input_sender_task:
            self._text_input_sender_task.cancel()
            try:
                await self._text_input_sender_task
            except asyncio.CancelledError:
                pass
            self._text_input_sender_task = None
        
        # 수신 태스크 취소
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        # 재연결 태스크 취소
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        
        # WebSocket 종료
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None
        
        logger.info("Disconnected from AI server")
        
        await publish(
            EventType.WS_DISCONNECTED,
            data={"session_id": self._session_id},
            source="network.ws_client"
        )
    
    async def send_message(self, msg_type: str, data: Dict[str, Any]) -> bool:
        """
        메시지 전송
        
        Args:
            msg_type: 메시지 타입
            data: 메시지 데이터
            
        Returns:
            전송 성공 여부
        """
        if self._websocket is None:
            logger.warning("Not connected to AI server (no websocket)")
            return False
        
        message = {
            "type": msg_type,
            "data": data,
            "session_id": self._session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent message: {msg_type}")
            return True
        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed during send: {e}")
            self._websocket = None
            # 재연결 트리거
            if self._running and not self._reconnect_task:
                self._reconnect_task = asyncio.create_task(self._reconnect())
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def _receive_loop(self):
        """메시지 수신 루프"""
        logger.debug("Message receive loop started")
        
        connection_alive = True
        
        try:
            while self._running and connection_alive:
                try:
                    # recv()가 연결 종료 시 예외를 던짐
                    message = await self._websocket.recv()
                    await self._handle_message(message)
                except websockets.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    connection_alive = False
                    self._websocket = None
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    # 기타 에러는 계속 시도
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
            return  # Don't reconnect if cancelled
        
        # 연결이 끊어지면 재연결 시도
        if self._running and not connection_alive:
            self._reconnect_task = asyncio.create_task(self._reconnect())
    
    async def _reconnect(self):
        """자동 재연결"""
        attempts = 0
        max_attempts = self._config.max_reconnect_attempts
        interval = self._config.reconnect_interval
        
        while self._running and attempts < max_attempts:
            attempts += 1
            logger.info(f"Reconnecting... (attempt {attempts}/{max_attempts})")
            
            await asyncio.sleep(interval)
            
            if await self.connect():
                logger.info("Reconnected to AI server")
                return
        
        logger.error("Max reconnection attempts reached")
        await publish(
            EventType.ERROR_OCCURRED,
            data={"error": "Failed to reconnect to AI server"},
            source="network.ws_client"
        )
    
    async def _handle_message(self, raw_message: str):
        """
        수신 메시지 처리
        
        Args:
            raw_message: 수신한 JSON 문자열
        """
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            data = message.get("data", {})
            
            logger.debug(f"Received message: {msg_type}")
            
            if msg_type == MessageType.TOOL_CALLS:
                await self._handle_tool_calls(data)
            elif msg_type == MessageType.STATUS:
                logger.info(f"Server status: {data.get('message', '')}")
            elif msg_type == MessageType.ERROR:
                logger.error(f"Server error: {data.get('error', '')}")
            elif msg_type == MessageType.ASR_RESULT:
                await self._handle_asr_result(data)
            elif msg_type == MessageType.TTS_CHUNK:
                await self._handle_tts_chunk(data)
            else:
                logger.debug(f"Unhandled message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")
    
    async def _handle_tool_calls(self, data: Dict[str, Any]):
        """
        tool_calls 메시지 처리
        
        LLM이 생성한 명령을 MCP_TOOL_CALL 이벤트로 변환하여 발행
        """
        commands = data.get("commands", [])
        
        if not commands:
            logger.warning("Empty tool_calls received")
            return
        
        logger.info(f"Received {len(commands)} tool call(s)")

        for i, cmd in enumerate(commands):
            tool_name = cmd.get("tool_name")
            arguments = cmd.get("arguments", {})
            description = cmd.get("description", "")
            
            # 고유 요청 ID 생성
            request_id = f"{self._session_id}_{datetime.now().timestamp()}_{i}"
            
            logger.info(f"  [{i+1}] {tool_name}: {description}")
            
            # MCP_TOOL_CALL 이벤트 발행
            await publish(
                EventType.MCP_TOOL_CALL,
                data={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "description": description
                },
                source="network.ws_client"
            )
    
    async def _handle_asr_result(self, data: Dict[str, Any]):
        """ASR 결과 처리 (로깅용)"""
        text = data.get("text", "")
        is_final = data.get("is_final", False)
        
        if is_final and text:
            logger.info(f"ASR result: {text}")
    
    async def _handle_tts_chunk(self, data: Dict[str, Any]):
        """TTS 청크 처리"""
        is_final = data.get("is_final", False)
        audio_hex = data.get("audio", "")
        text = data.get("text") or ""
        tts_id = data.get("tts_id") or ""
        segment_index = data.get("segment_index")
        segment_total = data.get("segment_total")

        if text:
            seg_label = ""
            if isinstance(segment_index, int) and isinstance(segment_total, int) and segment_total > 0:
                seg_label = f" [{segment_index + 1}/{segment_total}]"
            logger.info(f"TTS text{seg_label}: {text}")
        
        if audio_hex:
            # TODO: TTS 오디오 재생 구현
            await publish(
                EventType.TTS_AUDIO_RECEIVED,
                data={
                    "audio": bytes.fromhex(audio_hex),
                    "is_final": is_final,
                    "text": text,
                    "tts_id": tts_id,
                    "segment_index": segment_index,
                    "segment_total": segment_total,
                },
                source="network.ws_client"
            )
    
    async def _on_audio_ready(self, event):
        """
        AUDIO_READY 이벤트 핸들러
        
        AudioManager에서 발행한 오디오 청크를 AI 서버로 전송
        """
        data = event.data
        if not data:
            return
        
        audio_b64 = data.get("audio", "")
        seq = data.get("seq", 0)
        is_final = data.get("is_final", False)
        
        status = "FINAL" if is_final else "PARTIAL"
        logger.debug(f"Sending audio chunk: {status} #{seq}")
        
        # AI 서버로 audio_chunk 전송
        await self.send_message(
            MessageType.AUDIO_CHUNK,
            {
                "audio": audio_b64,
                "seq": seq,
                "is_final": is_final
            }
        )
    
    async def _on_mcp_result(self, event):
        """
        MCP_RESULT 이벤트 핸들러
        
        MCPHandler에서 발행한 결과를 AI 서버로 전송
        """
        data = event.data
        if not data:
            return
        
        request_id = data.get("request_id", "")
        success = data.get("success", False)
        result = data.get("result", {})
        error = data.get("error")
        page_data = data.get("page_data")
        tool_name = data.get("tool_name")
        arguments = data.get("arguments")
        
        logger.info(f"MCP result: request_id={request_id}, success={success}")
        
        # AI 서버로 결과 전송
        await self.send_message(
            MessageType.MCP_RESULT,
            {
                "request_id": request_id,
                "success": success,
                "result": result,
                "error": error,
                "page_data": page_data,
                "tool_name": tool_name,
                "arguments": arguments
            }
        )

    async def _on_hotkey_pressed(self, event):
        """Send interrupt to server on barge-in hotkey"""
        if not self.is_connected:
            return

        await self.send_message(
            MessageType.INTERRUPT,
            {"reason": "hotkey"}
        )

    async def _on_text_input_ready(self, event):
        """Queue text input to server (bypass ASR).

        Important: the WS connection can drop/reconnect; do not lose inputs.
        """
        text = (event.data or "").strip()
        if not text:
            return
        await self._text_input_queue.put(text)

    async def _text_input_sender_loop(self):
        """Send queued text inputs in order, waiting out reconnects."""
        while self._running:
            try:
                text = await self._text_input_queue.get()
            except asyncio.CancelledError:
                return

            if not self._running:
                return

            while self._running:
                if not self.is_connected:
                    await asyncio.sleep(0.5)
                    continue
                ok = await self.send_message(MessageType.USER_INPUT, {"text": text})
                if ok:
                    break
                await asyncio.sleep(0.5)

    async def _on_page_url_updated(self, event):
        """Send page URL updates to server."""
        if not self.is_connected:
            return
        data = event.data or {}
        url = data.get("url")
        page_id = data.get("page_id")
        if not url:
            return
        await self.send_message(
            MessageType.PAGE_UPDATE,
            {"url": url, "page_id": page_id}
        )
    
    async def _on_shutdown(self, _event):
        """종료 이벤트 핸들러"""
        await self.disconnect()
    
    async def start(self):
        """클라이언트 시작"""
        logger.info("Starting WSClient...")
        self._running = True
        if not self._text_input_sender_task:
            self._text_input_sender_task = asyncio.create_task(self._text_input_sender_loop())
        await self.connect()
    
    async def stop(self):
        """클라이언트 종료"""
        logger.info("Stopping WSClient...")
        await self.disconnect()
