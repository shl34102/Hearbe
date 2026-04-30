"""
MCPHandler 통합 테스트

이벤트 기반 아키텍처 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from core.event_bus import Event, EventType
from mcp.handler import MCPHandler


class TestMCPHandler:
    """MCPHandler 테스트"""

    # ---- 초기화 & 설정 테스트 ----

    def test_handler_init(self):
        """핸들러 초기화"""
        handler = MCPHandler()
        
        assert handler._tools is not None
        assert handler._ready is False
        assert handler._cdp_url is None

    def test_is_ready(self):
        """준비 상태 확인"""
        handler = MCPHandler()
        
        # 초기 상태
        assert handler.is_ready is False
        
        # ready 플래그만 설정 (연결 안됨)
        handler._ready = True
        assert handler.is_ready is False  # 도구가 연결 안됨
        
        # 도구 연결 시뮬레이션
        handler._tools._browser = MagicMock()
        handler._tools._browser.is_connected = Mock(return_value=True)
        assert handler.is_ready is True

    @patch("mcp.handler.event_bus")
    def test_setup_event_handlers(self, mock_event_bus):
        """이벤트 핸들러 등록"""
        handler = MCPHandler()
        
        handler.setup_event_handlers()
        
        # 3개의 이벤트 핸들러 등록 확인
        assert mock_event_bus.subscribe.call_count == 3
        
        # 각 이벤트 타입별 호출 확인
        calls = [call[0][0] for call in mock_event_bus.subscribe.call_args_list]
        assert EventType.BROWSER_READY in calls
        assert EventType.MCP_TOOL_CALL in calls
        assert EventType.APP_SHUTDOWN in calls

    # ---- 브라우저 준비 이벤트 테스트 ----

    @pytest.mark.asyncio
    @patch("mcp.handler.publish")
    async def test_on_browser_ready_success(self, mock_publish):
        """BROWSER_READY 이벤트로 정상 연결"""
        handler = MCPHandler()
        
        # BrowserTools Mock
        handler._tools.connect = AsyncMock(return_value=True)
        
        event = Event(
            type=EventType.BROWSER_READY,
            data={"cdp_url": "ws://localhost:9222"},
            source="test"
        )
        
        await handler._on_browser_ready(event)
        
        # CDP URL 저장 확인
        assert handler._cdp_url == "ws://localhost:9222"
        
        # 연결 시도 확인
        handler._tools.connect.assert_called_once_with("ws://localhost:9222")
        
        # ready 상태 확인
        assert handler._ready is True
        
        # MCP_SERVER_READY 이벤트 발행 확인
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == EventType.MCP_SERVER_READY
        assert call_args[1]["data"]["status"] == "ready"

    @pytest.mark.asyncio
    @patch("mcp.handler.publish")
    async def test_on_browser_ready_invalid_data(self, mock_publish):
        """잘못된 이벤트 데이터"""
        handler = MCPHandler()
        
        # cdp_url 없는 이벤트
        event = Event(
            type=EventType.BROWSER_READY,
            data={},
            source="test"
        )
        
        await handler._on_browser_ready(event)
        
        # 연결 시도 안함
        assert handler._cdp_url is None
        assert handler._ready is False
        
        # 이벤트 발행 안함
        mock_publish.assert_not_called()

    @pytest.mark.asyncio
    @patch("mcp.handler.publish")
    async def test_on_browser_ready_connection_fail(self, mock_publish):
        """연결 실패 시 에러 이벤트 발행"""
        handler = MCPHandler()
        
        # 연결 실패 시뮬레이션
        handler._tools.connect = AsyncMock(return_value=False)
        
        event = Event(
            type=EventType.BROWSER_READY,
            data={"cdp_url": "ws://invalid:9222"},
            source="test"
        )
        
        await handler._on_browser_ready(event)
        
        # ready 상태 안됨
        assert handler._ready is False
        
        # MCP_ERROR 이벤트 발행 확인
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == EventType.MCP_ERROR
        assert "Failed to connect" in call_args[1]["data"]["error"]

    # ---- 도구 호출 이벤트 테스트 ----

    @pytest.mark.asyncio
    @patch("mcp.handler.publish")
    async def test_on_tool_call_success(self, mock_publish):
        """정상적인 도구 호출 및 결과 발행"""
        handler = MCPHandler()
        handler._ready = True
        handler._tools._browser = MagicMock()
        handler._tools._browser.is_connected = Mock(return_value=True)
        
        # execute_tool Mock
        handler._tools.execute_tool = AsyncMock(
            return_value={"success": True, "current_url": "https://example.com"}
        )
        
        event = Event(
            type=EventType.MCP_TOOL_CALL,
            data={
                "request_id": "req-123",
                "tool_name": "navigate_to_url",
                "arguments": {"url": "https://example.com"}
            },
            source="test"
        )
        
        await handler._on_tool_call(event)
        
        # 도구 실행 확인
        handler._tools.execute_tool.assert_called_once_with(
            "navigate_to_url",
            {"url": "https://example.com"}
        )
        
        # MCP_RESULT 이벤트 발행 확인
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == EventType.MCP_RESULT
        
        result_data = call_args[1]["data"]
        assert result_data["request_id"] == "req-123"
        assert result_data["success"] is True
        assert result_data["result"]["current_url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_on_tool_call_not_ready(self):
        """MCP 미준비 상태에서 호출"""
        handler = MCPHandler()
        handler._ready = False
        
        with patch("mcp.handler.publish") as mock_publish:
            event = Event(
                type=EventType.MCP_TOOL_CALL,
                data={
                    "request_id": "req-456",
                    "tool_name": "navigate_to_url",
                    "arguments": {}
                },
                source="test"
            )
            
            await handler._on_tool_call(event)
            
            # 에러 결과 발행
            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            result_data = call_args[1]["data"]
            assert result_data["success"] is False
            assert "not ready" in result_data["error"]

    @pytest.mark.asyncio
    async def test_on_tool_call_missing_tool_name(self):
        """tool_name 누락"""
        handler = MCPHandler()
        handler._ready = True
        handler._tools._browser = MagicMock()
        handler._tools._browser.is_connected = Mock(return_value=True)
        
        with patch("mcp.handler.publish") as mock_publish:
            event = Event(
                type=EventType.MCP_TOOL_CALL,
                data={
                    "request_id": "req-789",
                    # tool_name 누락
                    "arguments": {}
                },
                source="test"
            )
            
            await handler._on_tool_call(event)
            
            # 에러 결과 발행
            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            result_data = call_args[1]["data"]
            assert result_data["success"] is False
            assert "Missing tool_name" in result_data["error"]

    @pytest.mark.asyncio
    async def test_on_tool_call_invalid_data(self):
        """잘못된 이벤트 데이터 (None)"""
        handler = MCPHandler()
        
        # data가 None인 이벤트
        event = Event(
            type=EventType.MCP_TOOL_CALL,
            data=None,
            source="test"
        )
        
        await handler._on_tool_call(event)
        
        # 아무것도 실행되지 않음 (로그만 기록)

    # ---- 결과 발행 테스트 ----

    @pytest.mark.asyncio
    @patch("mcp.handler.publish")
    async def test_publish_result_success(self, mock_publish):
        """성공 결과 발행"""
        handler = MCPHandler()
        
        await handler._publish_result(
            request_id="req-111",
            success=True,
            result={"data": "example"}
        )
        
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == EventType.MCP_RESULT
        
        data = call_args[1]["data"]
        assert data["request_id"] == "req-111"
        assert data["success"] is True
        assert data["result"]["data"] == "example"
        assert data["error"] is None

    @pytest.mark.asyncio
    @patch("mcp.handler.publish")
    async def test_publish_result_error(self, mock_publish):
        """에러 결과 발행"""
        handler = MCPHandler()
        
        await handler._publish_result(
            request_id="req-222",
            success=False,
            error="Something went wrong"
        )
        
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        
        data = call_args[1]["data"]
        assert data["request_id"] == "req-222"
        assert data["success"] is False
        assert data["error"] == "Something went wrong"

    # ---- 종료 처리 테스트 ----

    @pytest.mark.asyncio
    async def test_on_shutdown(self):
        """APP_SHUTDOWN 이벤트 처리"""
        handler = MCPHandler()
        handler._ready = True
        handler._tools.disconnect = AsyncMock()
        
        event = Event(
            type=EventType.APP_SHUTDOWN,
            data={},
            source="test"
        )
        
        await handler._on_shutdown(event)
        
        # stop() 호출 확인
        handler._tools.disconnect.assert_called_once()
        assert handler._ready is False

    @pytest.mark.asyncio
    async def test_stop(self):
        """핸들러 종료 및 리소스 정리"""
        handler = MCPHandler()
        handler._ready = True
        handler._tools.disconnect = AsyncMock()
        
        await handler.stop()
        
        assert handler._ready is False
        handler._tools.disconnect.assert_called_once()


# ============================================================================
# 통합 테스트 (실제 EventBus 사용)
# ============================================================================

@pytest.mark.integration
class TestMCPHandlerIntegration:
    """MCPHandler 실제 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, chrome_launcher):
        """전체 워크플로우 테스트: BROWSER_READY → TOOL_CALL → RESULT"""
        from core.event_bus import event_bus, publish
        
        handler = MCPHandler()
        handler.setup_event_handlers()
        await event_bus.start()
        
        # 결과를 저장할 변수
        mcp_ready_event = asyncio.Event()
        tool_result_event = asyncio.Event()
        
        async def on_mcp_ready(event):
            mcp_ready_event.set()
        
        async def on_mcp_result(event):
            tool_result_event.set()
        
        # 결과 이벤트 구독
        event_bus.subscribe(EventType.MCP_SERVER_READY, on_mcp_ready)
        event_bus.subscribe(EventType.MCP_RESULT, on_mcp_result)
        
        # 1. BROWSER_READY 이벤트 발행
        await publish(
            EventType.BROWSER_READY,
            data={"cdp_url": chrome_launcher._cdp_url},
            source="test"
        )
        
        # 이벤트 처리 대기
        await asyncio.wait_for(mcp_ready_event.wait(), timeout=5)
        
        assert handler.is_ready is True
        
        # 2. MCP_TOOL_CALL 이벤트 발행
        await publish(
            EventType.MCP_TOOL_CALL,
            data={
                "request_id": "integration-test-1",
                "tool_name": "navigate_to_url",
                "arguments": {"url": "https://www.example.com"}
            },
            source="test"
        )
        
        # 이벤트 처리 대기
        await asyncio.wait_for(tool_result_event.wait(), timeout=10)
        
        # 정리
        await handler.stop()
        await event_bus.stop()


import asyncio
