"""
BrowserTools 유닛 테스트

Mock 기반 테스트와 실제 브라우저 통합 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from mcp.tools import BrowserTools


# ============================================================================
# Mock 기반 테스트 (빠른 유닛 테스트)
# ============================================================================

class TestBrowserToolsMock:
    """BrowserTools Mock 기반 테스트"""

    # ---- 연결 관리 테스트 ----

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_playwright, mock_browser, mock_context, mock_page):
        """CDP URL로 정상 연결"""
        tools = BrowserTools()
        
        # Playwright Mock 설정
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("mcp.tools.async_playwright") as playwright_patch:
            playwright_patch.return_value.start = AsyncMock(return_value=mock_playwright)
            
            result = await tools.connect("ws://localhost:9222")
            
            assert result is True
            assert tools.is_connected is True
            mock_playwright.chromium.connect_over_cdp.assert_called_once_with("ws://localhost:9222")

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, mock_playwright, mock_browser):
        """이미 연결된 상태에서 재연결 시도"""
        tools = BrowserTools()
        tools._browser = mock_browser
        
        result = await tools.connect("ws://localhost:9222")
        
        assert result is True
        # 재연결 시도 안함
        assert mock_playwright.chromium.connect_over_cdp.call_count == 0

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """잘못된 URL로 연결 실패"""
        tools = BrowserTools()
        
        with patch("mcp.tools.async_playwright") as playwright_patch:
            mock_pw = AsyncMock()
            mock_pw.chromium.connect_over_cdp = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            playwright_patch.return_value.start = AsyncMock(return_value=mock_pw)
            
            result = await tools.connect("invalid_url")
            
            assert result is False
            assert tools.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_browser, mock_playwright):
        """연결 해제 및 리소스 정리"""
        tools = BrowserTools()
        tools._browser = mock_browser
        tools._playwright = mock_playwright
        tools._page = Mock()
        
        await tools.disconnect()
        
        assert tools._browser is None
        assert tools._playwright is None
        assert tools._page is None
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_connected(self, mock_browser):
        """연결 상태 확인"""
        tools = BrowserTools()
        
        # 미연결 상태
        assert tools.is_connected is False
        
        # 연결 상태
        tools._browser = mock_browser
        assert tools.is_connected is True

    # ---- 네비게이션 테스트 ----

    @pytest.mark.asyncio
    async def test_navigate_to_url_success(self, mock_page):
        """URL 이동 성공"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.url = "https://example.com"
        
        result = await tools.navigate_to_url("https://example.com")
        
        assert result["success"] is True
        assert result["current_url"] == "https://example.com"
        mock_page.goto.assert_called_once_with(
            "https://example.com", 
            wait_until="domcontentloaded"
        )

    @pytest.mark.asyncio
    async def test_navigate_to_url_not_connected(self):
        """미연결 상태에서 네비게이션 실패"""
        tools = BrowserTools()
        
        result = await tools.navigate_to_url("https://example.com")
        
        assert result["success"] is False
        assert "Not connected" in result["error"]

    @pytest.mark.asyncio
    async def test_navigate_to_url_failure(self, mock_page):
        """네비게이션 실패 (타임아웃 등)"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.goto.side_effect = Exception("Navigation timeout")
        
        result = await tools.navigate_to_url("https://invalid-url.com")
        
        assert result["success"] is False
        assert "error" in result

    # ---- 요소 상호작용 테스트 ----

    @pytest.mark.asyncio
    async def test_click_element_success(self, mock_page):
        """요소 클릭 성공"""
        tools = BrowserTools()
        tools._page = mock_page
        
        result = await tools.click_element("button#submit")
        
        assert result["success"] is True
        assert result["element_found"] is True
        mock_page.wait_for_selector.assert_called_once_with("button#submit", timeout=5000)
        mock_page.click.assert_called_once_with("button#submit")

    @pytest.mark.asyncio
    async def test_click_element_timeout(self, mock_page):
        """요소 찾기 타임아웃"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.wait_for_selector.side_effect = Exception("Timeout")
        
        result = await tools.click_element("button#not-exist", wait_timeout=1000)
        
        assert result["success"] is False
        assert result["element_found"] is False

    @pytest.mark.asyncio
    async def test_click_element_not_connected(self):
        """미연결 상태에서 클릭 실패"""
        tools = BrowserTools()
        
        result = await tools.click_element("button")
        
        assert result["success"] is False
        assert "Not connected" in result["error"]

    @pytest.mark.asyncio
    async def test_fill_input(self, mock_page):
        """입력 필드 채우기"""
        tools = BrowserTools()
        tools._page = mock_page
        
        result = await tools.fill_input("input#username", "test_user")
        
        assert result["success"] is True
        mock_page.fill.assert_called_once_with("input#username", "test_user")

    @pytest.mark.asyncio
    async def test_fill_input_failure(self, mock_page):
        """입력 필드 채우기 실패"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.fill.side_effect = Exception("Element not found")
        
        result = await tools.fill_input("input#not-exist", "value")
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_text_success(self, mock_page):
        """텍스트 추출 성공"""
        tools = BrowserTools()
        tools._page = mock_page
        
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="Hello World")
        mock_page.query_selector.return_value = mock_element
        
        result = await tools.get_text("h1.title")
        
        assert result["success"] is True
        assert result["text"] == "Hello World"
        mock_page.query_selector.assert_called_once_with("h1.title")

    @pytest.mark.asyncio
    async def test_get_text_element_not_found(self, mock_page):
        """요소를 찾을 수 없음"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.query_selector.return_value = None
        
        result = await tools.get_text("h1.not-exist")
        
        assert result["success"] is False
        assert "Element not found" in result["error"]

    # ---- 스크린샷 & 스크롤 테스트 ----

    @pytest.mark.asyncio
    async def test_take_screenshot(self, mock_page):
        """스크린샷 캡처"""
        tools = BrowserTools()
        tools._page = mock_page
        
        result = await tools.take_screenshot(full_page=True)
        
        assert result["success"] is True
        assert "screenshot_base64" in result
        mock_page.screenshot.assert_called_once_with(full_page=True)

    @pytest.mark.asyncio
    async def test_take_screenshot_failure(self, mock_page):
        """스크린샷 캡처 실패"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.screenshot.side_effect = Exception("Screenshot failed")
        
        result = await tools.take_screenshot()
        
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_scroll_down(self, mock_page):
        """아래로 스크롤"""
        tools = BrowserTools()
        tools._page = mock_page
        
        result = await tools.scroll("down", amount=500)
        
        assert result["success"] is True
        mock_page.mouse.wheel.assert_called_once_with(0, 500)

    @pytest.mark.asyncio
    async def test_scroll_up(self, mock_page):
        """위로 스크롤"""
        tools = BrowserTools()
        tools._page = mock_page
        
        result = await tools.scroll("up", amount=300)
        
        assert result["success"] is True
        mock_page.mouse.wheel.assert_called_once_with(0, -300)

    # ---- 도구 실행 테스트 ----

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, mock_page):
        """유효한 도구 실행"""
        tools = BrowserTools()
        tools._page = mock_page
        mock_page.url = "https://example.com"
        
        result = await tools.execute_tool("navigate_to_url", {"url": "https://example.com"})
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        """알 수 없는 도구 이름"""
        tools = BrowserTools()
        
        result = await tools.execute_tool("unknown_tool", {})
        
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_args(self, mock_page):
        """잘못된 인자"""
        tools = BrowserTools()
        tools._page = mock_page
        
        # navigate_to_url은 'url' 인자 필요
        result = await tools.execute_tool("navigate_to_url", {"invalid_arg": "value"})
        
        assert result["success"] is False
        assert "Invalid arguments" in result["error"]


# ============================================================================
# 통합 테스트 (실제 브라우저 사용)
# ============================================================================

@pytest.mark.integration
class TestBrowserToolsIntegration:
    """BrowserTools 실제 브라우저 통합 테스트"""

    @pytest.mark.asyncio
    async def test_real_browser_connection(self, chrome_launcher):
        """실제 브라우저에 연결"""
        tools = BrowserTools()
        
        result = await tools.connect(chrome_launcher._cdp_url)
        
        assert result is True
        assert tools.is_connected is True
        
        await tools.disconnect()

    @pytest.mark.asyncio
    async def test_real_browser_navigation(self, real_browser):
        """실제 브라우저에서 네비게이션"""
        tools = BrowserTools()
        tools._playwright = real_browser["playwright"]
        tools._browser = real_browser["browser"]
        tools._page = real_browser["page"]
        
        result = await tools.navigate_to_url("https://www.example.com")
        
        assert result["success"] is True
        assert "example.com" in result["current_url"]

    @pytest.mark.asyncio
    async def test_real_browser_get_text(self, real_browser):
        """실제 브라우저에서 텍스트 추출"""
        tools = BrowserTools()
        tools._playwright = real_browser["playwright"]
        tools._browser = real_browser["browser"]
        tools._page = real_browser["page"]
        
        # example.com으로 이동
        await tools.navigate_to_url("https://www.example.com")
        
        # h1 텍스트 추출
        result = await tools.get_text("h1")
        
        assert result["success"] is True
        assert len(result["text"]) > 0

    @pytest.mark.asyncio
    async def test_real_browser_screenshot(self, real_browser):
        """실제 브라우저에서 스크린샷"""
        tools = BrowserTools()
        tools._playwright = real_browser["playwright"]
        tools._browser = real_browser["browser"]
        tools._page = real_browser["page"]
        
        # example.com으로 이동
        await tools.navigate_to_url("https://www.example.com")
        
        result = await tools.take_screenshot()
        
        assert result["success"] is True
        assert len(result["screenshot_base64"]) > 0
