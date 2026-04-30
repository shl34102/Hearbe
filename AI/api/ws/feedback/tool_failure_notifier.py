# -*- coding: utf-8 -*-
"""
Tool failure notifier.

Emits user-facing TTS feedback when tool execution fails.
"""

from typing import Optional, Dict, Any

from services.llm.sites.site_manager import get_page_type


class ToolFailureNotifier:
    """Sends minimal failure feedback for failed tool calls."""

    def __init__(self, sender):
        self._sender = sender

    async def handle_mcp_result(
        self,
        session_id: str,
        tool_name: Optional[str],
        arguments: Optional[Dict[str, Any]],
        success: bool,
        handled: bool = False,
        current_url: Optional[str] = None,
    ):
        if success or handled:
            return

        if tool_name not in ("click", "click_element", "click_text"):
            return

        target = ""
        if arguments:
            if tool_name == "click_text":
                target = (arguments.get("text") or "").strip()
            elif tool_name in ("click", "click_element"):
                target = (arguments.get("selector") or "").strip()

        is_selector_like = any(token in target for token in ("[", "]", ".", "#", ">", "pad-key", "data-key"))
        is_checkout = bool(current_url and get_page_type(current_url) == "checkout")

        if target and target not in ("그거", "이거", "저거", "그것", "이것", "저것"):
            if is_selector_like or is_checkout:
                msg = "오류가 발생했습니다. 다시 말씀해 주세요."
            else:
                msg = f"'{target}'을 찾지 못했습니다. 다시 말씀해 주세요."
        else:
            msg = "오류가 발생했습니다. 다시 말씀해 주세요."

        await self._sender.send_tts_response(session_id, msg)
