"""
pytest 공용 fixture 정의

Mock 기반 테스트와 실제 브라우저 통합 테스트를 위한 fixtures
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import AsyncGenerator


# ============================================================================
# Mock Fixtures (빠른 테스트용)
# ============================================================================

@pytest.fixture
def mock_playwright():
    """Playwright Mock"""
    playwright = AsyncMock()
    playwright.chromium = AsyncMock()
    playwright.chromium.connect_over_cdp = AsyncMock()
    playwright.stop = AsyncMock()
    return playwright


@pytest.fixture
def mock_browser():
    """Browser Mock"""
    browser = AsyncMock()
    browser.is_connected = Mock(return_value=True)
    browser.close = AsyncMock()
    browser.contexts = []
    browser.new_context = AsyncMock()
    return browser


@pytest.fixture
def mock_page():
    """Page Mock"""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.url = "https://example.com"
    page.mouse = AsyncMock()
    page.mouse.wheel = AsyncMock()
    return page


@pytest.fixture
def mock_context():
    """BrowserContext Mock"""
    context = AsyncMock()
    context.new_page = AsyncMock()
    context.pages = []
    return context


@pytest.fixture
def mock_event_bus():
    """EventBus Mock"""
    event_bus = Mock()
    event_bus.subscribe = Mock()
    event_bus.publish = AsyncMock()
    return event_bus


# ============================================================================
# Integration Test Fixtures (실제 브라우저 사용)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 (세션 전체에서 재사용)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def chrome_launcher():
    """실제 ChromeLauncher 인스턴스 (통합 테스트용)"""
    from browser.launcher import ChromeLauncher
    
    launcher = ChromeLauncher()
    started = await launcher.start()
    
    if not started:
        pytest.skip("Chrome을 실행할 수 없습니다")
    
    yield launcher
    
    # 종료
    await launcher.stop()


@pytest.fixture
async def real_browser(chrome_launcher):
    """실제 Playwright 브라우저 연결 (통합 테스트용)"""
    from playwright.async_api import async_playwright
    
    if not chrome_launcher._cdp_url:
        pytest.skip("CDP URL을 얻을 수 없습니다")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.connect_over_cdp(chrome_launcher._cdp_url)
    
    # 기존 페이지 또는 새 페이지 생성
    contexts = browser.contexts
    if contexts and contexts[0].pages:
        page = contexts[0].pages[0]
    else:
        context = await browser.new_context()
        page = await context.new_page()
    
    yield {"playwright": playwright, "browser": browser, "page": page}
    
    # 정리
    await browser.close()
    await playwright.stop()


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def sample_cdp_url():
    """샘플 CDP URL"""
    return "ws://127.0.0.1:9222/devtools/browser/test-id"


@pytest.fixture
def sample_event():
    """샘플 Event 객체"""
    from core.event_bus import Event, EventType
    
    def _create_event(event_type: EventType, data: dict = None):
        return Event(event_type=event_type, data=data or {}, source="test")
    
    return _create_event
