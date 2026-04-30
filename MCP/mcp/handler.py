"""
MCP 핸들러 모듈

MCP_TOOL_CALL 이벤트를 처리하고 브라우저 제어 도구 실행
"""

import logging
from typing import Optional

from core.event_bus import event_bus, EventType, publish, Event
from core.config import get_config
from .tools import BrowserTools

logger = logging.getLogger(__name__)


class MCPHandler:
    """
    MCP 도구 호출 핸들러

    이벤트 버스를 통해 도구 호출 요청을 받아 실행하고 결과 반환
    """

    def __init__(self):
        self._config = get_config().mcp
        self._tools = BrowserTools()
        self._cdp_url: Optional[str] = None
        self._ready = False

    @property
    def is_ready(self) -> bool:
        """MCP 핸들러 준비 상태"""
        return self._ready and self._tools.is_connected

    def setup_event_handlers(self):
        """이벤트 핸들러 등록"""
        event_bus.subscribe(EventType.BROWSER_READY, self._on_browser_ready)
        event_bus.subscribe(EventType.MCP_TOOL_CALL, self._on_tool_call)
        event_bus.subscribe(EventType.APP_SHUTDOWN, self._on_shutdown)
        logger.info("MCP event handlers registered")

    async def _on_browser_ready(self, event: Event):
        """브라우저 준비 완료 이벤트 처리"""
        data = event.data
        if not data or "cdp_url" not in data:
            logger.error("Invalid BROWSER_READY event data")
            return

        self._cdp_url = data["cdp_url"]
        logger.info(f"Browser ready, CDP URL: {self._cdp_url}")

        # 브라우저에 연결
        connected = await self._tools.connect(self._cdp_url)
        if connected:
            self._ready = True
            await publish(
                EventType.MCP_SERVER_READY,
                data={"status": "ready"},
                source="mcp.handler"
            )
            logger.info("MCP handler is ready")
        else:
            await publish(
                EventType.MCP_ERROR,
                data={"error": "Failed to connect to browser"},
                source="mcp.handler"
            )

    async def _on_tool_call(self, event: Event):
        """도구 호출 이벤트 처리"""
        data = event.data
        if not data:
            logger.error("Invalid MCP_TOOL_CALL event data")
            return

        request_id = data.get("request_id", "unknown")
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})

        logger.info(f"Tool call received: {tool_name} (request_id={request_id})")

        if not self.is_ready:
            await self._publish_result(
                request_id=request_id,
                success=False,
                error="MCP handler not ready"
            )
            return

        if not tool_name:
            await self._publish_result(
                request_id=request_id,
                success=False,
                error="Missing tool_name"
            )
            return

        # 도구 실행
        result = await self._tools.execute_tool(tool_name, arguments)

        # 결과 발행
        page_data = None
        if isinstance(result, dict) and result.get("products"):
            page_data = {
                "products": result.get("products", []),
                "url": result.get("page_url")
            }

        await self._publish_result(
            request_id=request_id,
            success=result.get("success", False),
            result=result,
            error=result.get("error"),
            page_data=page_data,
            tool_name=tool_name,
            arguments=arguments
        )

    async def _publish_result(
        self,
        request_id: str,
        success: bool,
        result: dict = None,
        error: str = None,
        page_data: dict = None,
        tool_name: str = None,
        arguments: dict = None
    ):
        """도구 실행 결과 발행"""
        await publish(
            EventType.MCP_RESULT,
            data={
                "request_id": request_id,
                "success": success,
                "result": result,
                "error": error,
                "page_data": page_data,
                "tool_name": tool_name,
                "arguments": arguments
            },
            source="mcp.handler"
        )
        logger.info(f"Tool result published: request_id={request_id}, success={success}")

    async def _on_shutdown(self, _event: Event):
        """종료 이벤트 처리"""
        await self.stop()

    async def stop(self):
        """핸들러 종료"""
        logger.info("Stopping MCP handler...")
        self._ready = False
        await self._tools.disconnect()
        logger.info("MCP handler stopped")
