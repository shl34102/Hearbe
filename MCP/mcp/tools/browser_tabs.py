"""
Browser tab helpers.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BrowserTabsMixin:
    """Tab detection and focus helpers."""

    async def wait_for_new_page(
        self,
        timeout_ms: int = 1500,
        focus: bool = True,
    ) -> Dict[str, Any]:
        page = await self._get_active_page()
        if not page:
            return {"success": False, "error": "Not connected to browser"}

        previous_url = page.url
        context = page.context
        before_pages = [p for p in context.pages if not p.is_closed()]
        before_set = set(before_pages)
        new_page = None

        try:
            new_page = await context.wait_for_event("page", timeout=timeout_ms)
        except Exception:
            new_page = None

        if not new_page:
            after_pages = [p for p in context.pages if not p.is_closed()]
            for candidate in after_pages:
                if candidate not in before_set:
                    new_page = candidate
                    break

        if not new_page:
            return {
                "success": True,
                "new_page": False,
                "previous_url": previous_url,
                "current_url": page.url,
                "url_changed": False,
            }

        if focus:
            try:
                await new_page.bring_to_front()
            except Exception:
                pass

        try:
            self._page = new_page
        except Exception:
            pass

        current_url = new_page.url
        logger.info(f"Detected new page and focused: {previous_url} -> {current_url}")
        return {
            "success": True,
            "new_page": True,
            "previous_url": previous_url,
            "current_url": current_url,
            "url_changed": previous_url != current_url,
        }

    async def get_pages(self) -> Dict[str, Any]:
        """
        Return a list of open pages/tabs.

        Returns:
            {"success": bool, "pages": list, "count": int}
        """
        if not self.is_connected:
            return {"success": False, "error": "Not connected to browser", "pages": []}

        try:
            pages: list[Dict[str, Any]] = []
            for context in self._browser.contexts:
                for page in context.pages:
                    if page.is_closed():
                        continue
                    url = page.url or ""
                    title = ""
                    if "/" in url:
                        parts = url.split("/")
                        if len(parts) > 2:
                            title = parts[2]
                    pages.append(
                        {
                            "index": len(pages),
                            "url": url,
                            "title": title or url,
                            "is_current": False,
                        }
                    )

            if pages:
                pages[-1]["is_current"] = True
            return {"success": True, "pages": pages, "count": len(pages)}
        except Exception as e:
            logger.error(f"Get pages failed: {e}")
            return {"success": False, "error": str(e), "pages": []}
