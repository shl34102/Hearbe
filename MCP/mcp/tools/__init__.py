"""
브라우저 제어 도구 모듈

Playwright를 사용하여 CDP로 연결된 브라우저 제어
"""

import logging
from typing import Any, Dict

from mcp.tool_utils import normalize_tool_call
from .browser_connection import BrowserConnectionMixin
from .browser_actions import BrowserActionsMixin
from .browser_extraction import BrowserExtractionMixin
from .browser_state import BrowserStateMixin
from .browser_utilities import BrowserUtilitiesMixin
from .browser_tabs import BrowserTabsMixin

logger = logging.getLogger(__name__)


class BrowserTools(
    BrowserConnectionMixin,
    BrowserActionsMixin,
    BrowserExtractionMixin,
    BrowserStateMixin,
    BrowserUtilitiesMixin,
    BrowserTabsMixin,
):
    """
    브라우저 제어 도구

    Playwright를 통해 CDP 연결된 Chrome 브라우저 조작
    여러 Mixin 클래스를 조합하여 기능 제공
    """

    def __init__(self):
        # 모든 Mixin 초기화
        BrowserConnectionMixin.__init__(self)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        도구 실행

        Args:
            tool_name: 도구 이름
            arguments: 도구 인자

        Returns:
            도구 실행 결과
        """
        tool_name, args = normalize_tool_call(tool_name, arguments)

        tools = {
            "navigate_to_url": self.navigate_to_url,
            "click_element": self.click_element,
            "fill_input": self.fill_input,
            "get_text": self.get_text,
            "extract": self.extract,
            "extract_detail": self.extract_detail,
            "extract_cart": self.extract_cart,
            "extract_order_detail": self.extract_order_detail,
            "extract_order_list": self.extract_order_list,
            "get_dom_snapshot": self.get_dom_snapshot,
            "take_screenshot": self.take_screenshot,
            "screenshot_element": self.screenshot_element,
            "scroll": self.scroll,
            "press_key": self.press_key,
            "wait": self.wait,
            "click_text": self.click_text,
            "get_visible_buttons": self.get_visible_buttons,
            "get_attribute_list": self.get_attribute_list,
            "check_login_status": self.check_login_status,
            "get_user_session": self.get_user_session,
            "get_user_type": self.get_user_type,
            "get_pages": self.get_pages,
            "wait_for_new_page": self.wait_for_new_page,
            "wait_for_selector": self.wait_for_selector,
            "handle_captcha_modal": self.handle_captcha_modal,
        }

        if tool_name not in tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        tool_func = tools[tool_name]

        try:
            result = await tool_func(**args)
            if isinstance(result, dict):
                try:
                    page = await self._get_active_page()
                    if page and page.url:
                        result.setdefault("current_url", page.url)
                except Exception:
                    pass
            return result
        except TypeError as e:
            return {"success": False, "error": f"Invalid arguments: {e}"}


__all__ = ["BrowserTools"]
