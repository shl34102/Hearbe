"""
브라우저 유틸리티 모듈

네비게이션, 대기, 스크린샷, 스크롤 등 유틸리티 기능
"""

import asyncio
import base64
import logging
from typing import Any, Dict, Optional

from mcp.tool_utils import resolve_frame_context

logger = logging.getLogger(__name__)


class BrowserUtilitiesMixin:
    """브라우저 유틸리티 기능을 담당하는 Mixin 클래스"""

    async def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """
        URL로 이동

        Args:
            url: 이동할 URL

        Returns:
            {"success": bool, "previous_url": str, "current_url": str, "url_changed": bool}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        previous_url = page.url
        try:
            await page.goto(url, wait_until="domcontentloaded")
            current_url = page.url
            logger.info(f"Navigated from {previous_url} to {current_url}")
            return {
                "success": True,
                "previous_url": previous_url,
                "current_url": current_url,
                "url_changed": previous_url != current_url,
            }

        except Exception as e:
            current_url = page.url if page else ""
            logger.error(f"Navigation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "previous_url": previous_url,
                "current_url": current_url,
                "url_changed": previous_url != current_url,
            }

    async def wait(self, ms: int = 1000) -> Dict[str, Any]:
        """
        대기
        Args:
            ms: 대기 시간 (ms)

        Returns:
            {"success": bool}
        """
        if ms < 0:
            return {"success": False, "error": "Invalid wait time"}
        await asyncio.sleep(ms / 1000)
        return {"success": True}

    async def take_screenshot(self, full_page: bool = False) -> Dict[str, Any]:
        """
        스크린샷 캡처

        Args:
            full_page: 전체 페이지 캡처 여부

        Returns:
            {"success": bool, "screenshot_base64": str}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        try:
            screenshot_bytes = await page.screenshot(full_page=full_page)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            logger.info(f"Screenshot taken (full_page={full_page})")
            return {"success": True, "screenshot_base64": screenshot_base64}

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    async def screenshot_element(
        self,
        selector: str,
        frame_selector: Optional[str] = None,
        frame_name: Optional[str] = None,
        frame_url: Optional[str] = None,
        frame_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        특정 요소 스크린샷 캡처

        Args:
            selector: CSS selector
            frame_selector: iframe CSS selector (optional)
            frame_name: iframe name attribute (optional)
            frame_url: iframe URL match (optional)
            frame_index: iframe index (optional)

        Returns:
            {"success": bool, "screenshot_base64": str}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        try:
            context_type, context, error = resolve_frame_context(
                page,
                frame_selector=frame_selector,
                frame_name=frame_name,
                frame_url=frame_url,
                frame_index=frame_index,
            )
            if error:
                return {"success": False, "error": error}

            locator = context.locator(selector) if context_type == "frame_locator" else context.locator(selector)
            if await locator.count() == 0:
                return {"success": False, "error": "Element not found"}

            element = locator.first
            screenshot_bytes = await element.screenshot()
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            logger.info(f"Element screenshot taken: {selector}")
            return {"success": True, "screenshot_base64": screenshot_base64}
        except Exception as e:
            logger.error(f"Element screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    async def handle_captcha_modal(self) -> Dict[str, Any]:
        """
        Detect captcha modal and click audio button if present.

        Returns:
            {"success": bool, "captcha_found": bool, "audio_clicked": bool}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        try:
            captcha_input = page.locator(''
                "input[placeholder*='자동입력'], "
                "input[placeholder*='보안문자'], "
                "input[placeholder*='방지문자']"
            )
            input_visible = False
            if await captcha_input.count() > 0:
                try:
                    input_visible = await captcha_input.first.is_visible()
                except Exception:
                    input_visible = False

            audio_btn = page.locator("button:has-text('음성으로 듣기')")
            refresh_btn = page.locator("button:has-text('새로고침')")
            audio_visible = await audio_btn.count() > 0 and await audio_btn.first.is_visible()
            refresh_visible = await refresh_btn.count() > 0 and await refresh_btn.first.is_visible()

            captcha_found = input_visible and (audio_visible or refresh_visible)

            audio_clicked = False
            if captcha_found and audio_visible:
                await audio_btn.first.click()
                audio_clicked = True

            return {
                "success": True,
                "captcha_found": captcha_found,
                "audio_clicked": audio_clicked,
            }
        except Exception as e:
            logger.error(f"Captcha handling failed: {e}")
            return {"success": False, "error": str(e), "captcha_found": False, "audio_clicked": False}

    async def scroll(self, direction: str, amount: int = 500) -> Dict[str, Any]:
        """
        페이지 스크롤

        Args:
            direction: 스크롤 방향 ("up" 또는 "down")
            amount: 스크롤 양(px)

        Returns:
            {"success": bool}
        """
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        try:
            delta = -amount if direction == "up" else amount
            await page.mouse.wheel(0, delta)
            logger.info(f"Scrolled {direction} by {amount}px")
            return {"success": True}

        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return {"success": False, "error": str(e)}
