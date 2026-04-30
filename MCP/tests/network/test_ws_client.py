"""
WebSocket 클라이언트 테스트

Mock 기반 단위 테스트
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.event_bus import EventType, Event


class MockWebSocket:
    """Mock WebSocket connection"""
    
    def __init__(self):
        self.open = True
        self.sent_messages = []
        self.receive_queue = asyncio.Queue()
    
    async def send(self, message):
        self.sent_messages.append(message)
    
    async def recv(self):
        return await self.receive_queue.get()
    
    async def close(self):
        self.open = False
    
    async def add_message(self, message):
        await self.receive_queue.put(message)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket fixture"""
    return MockWebSocket()


@pytest.fixture
def mock_config():
    """Mock config fixture"""
    config = Mock()
    config.network = Mock()
    config.network.ws_url = "ws://localhost:8000/ws"
    config.network.reconnect_interval = 1
    config.network.max_reconnect_attempts = 3
    return config


@pytest.fixture
def mock_event_bus():
    """Mock event bus fixture"""
    with patch('network.ws_client.event_bus') as mock_bus:
        mock_bus.subscribe = Mock()
        yield mock_bus


class TestWSClientMessageHandling:
    """메시지 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_handle_tool_calls_publishes_events(self, mock_event_bus):
        """tool_calls 메시지가 MCP_TOOL_CALL 이벤트로 변환되는지 테스트"""
        with patch('network.ws_client.get_config') as mock_get_config:
            mock_get_config.return_value = Mock(network=Mock(
                ws_url="ws://localhost:8000/ws",
                reconnect_interval=1,
                max_reconnect_attempts=3
            ))
            with patch('network.ws_client.publish') as mock_publish:
                from network.ws_client import WSClient
                
                client = WSClient()
                
                # tool_calls 데이터
                data = {
                    "commands": [
                        {
                            "tool_name": "navigate_to_url",
                            "arguments": {"url": "https://www.coupang.com"},
                            "description": "쿠팡 홈페이지로 이동"
                        },
                        {
                            "tool_name": "fill_input",
                            "arguments": {"selector": "input[name='q']", "value": "우유"},
                            "description": "검색어 입력"
                        }
                    ]
                }
                
                # 메시지 처리
                await client._handle_tool_calls(data)
                
                # 이벤트 발행 확인
                assert mock_publish.call_count == 2
                
                # 첫 번째 호출 검증
                first_call = mock_publish.call_args_list[0]
                assert first_call[0][0] == EventType.MCP_TOOL_CALL
                assert first_call[1]["data"]["tool_name"] == "navigate_to_url"
                
                # 두 번째 호출 검증
                second_call = mock_publish.call_args_list[1]
                assert second_call[0][0] == EventType.MCP_TOOL_CALL
                assert second_call[1]["data"]["tool_name"] == "fill_input"
    
    @pytest.mark.asyncio
    async def test_handle_empty_tool_calls(self, mock_event_bus):
        """빈 tool_calls 처리 테스트"""
        with patch('network.ws_client.get_config') as mock_get_config:
            mock_get_config.return_value = Mock(network=Mock(
                ws_url="ws://localhost:8000/ws",
                reconnect_interval=1,
                max_reconnect_attempts=3
            ))
            with patch('network.ws_client.publish') as mock_publish:
                from network.ws_client import WSClient
                
                client = WSClient()
                
                # 빈 commands
                await client._handle_tool_calls({"commands": []})
                
                # 이벤트가 발행되지 않아야 함
                mock_publish.assert_not_called()


class TestWSClientMCPResult:
    """MCP 결과 전송 테스트"""
    
    @pytest.mark.asyncio
    async def test_on_mcp_result_sends_message(self, mock_event_bus):
        """MCP_RESULT 이벤트가 mcp_result 메시지로 전송되는지 테스트"""
        with patch('network.ws_client.get_config') as mock_get_config:
            mock_get_config.return_value = Mock(network=Mock(
                ws_url="ws://localhost:8000/ws",
                reconnect_interval=1,
                max_reconnect_attempts=3
            ))
            from network.ws_client import WSClient, MessageType
            
            client = WSClient()
            client._websocket = MockWebSocket()
            
            # MCP_RESULT 이벤트 생성
            event = Event(
                type=EventType.MCP_RESULT,
                data={
                    "request_id": "test_123",
                    "success": True,
                    "result": {"current_url": "https://www.coupang.com"},
                    "error": None
                },
                source="mcp.handler"
            )
            
            # 핸들러 호출
            await client._on_mcp_result(event)
            
            # 전송된 메시지 확인
            assert len(client._websocket.sent_messages) == 1
            
            sent = json.loads(client._websocket.sent_messages[0])
            assert sent["type"] == MessageType.MCP_RESULT
            assert sent["data"]["success"] == True
            assert sent["data"]["request_id"] == "test_123"


class TestWSClientConnection:
    """연결 관리 테스트"""
    
    @pytest.mark.asyncio
    async def test_is_connected_property(self, mock_event_bus):
        """is_connected 속성 테스트"""
        with patch('network.ws_client.get_config') as mock_get_config:
            mock_get_config.return_value = Mock(network=Mock(
                ws_url="ws://localhost:8000/ws",
                reconnect_interval=1,
                max_reconnect_attempts=3
            ))
            from network.ws_client import WSClient
            
            client = WSClient()
            
            # 초기 상태: 연결 안됨
            assert client.is_connected == False
            
            # WebSocket Mock 할당
            mock_ws = MockWebSocket()
            mock_ws.open = True
            client._websocket = mock_ws
            
            # 연결됨
            assert client.is_connected == True
            
            # 연결 종료
            mock_ws.open = False
            assert client.is_connected == False
    
    @pytest.mark.asyncio
    async def test_session_id_generation(self, mock_event_bus):
        """세션 ID 자동 생성 테스트"""
        with patch('network.ws_client.get_config') as mock_get_config:
            mock_get_config.return_value = Mock(network=Mock(
                ws_url="ws://localhost:8000/ws",
                reconnect_interval=1,
                max_reconnect_attempts=3
            ))
            from network.ws_client import WSClient
            
            client1 = WSClient()
            client2 = WSClient()
            
            # 세션 ID가 UUID 형식인지 확인
            assert len(client1.session_id) == 36
            assert "-" in client1.session_id
            
            # 다른 클라이언트는 다른 세션 ID
            assert client1.session_id != client2.session_id
