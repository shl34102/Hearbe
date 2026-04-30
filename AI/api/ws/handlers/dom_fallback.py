# -*- coding: utf-8 -*-
"""
DOM fallback manager.

On tool failure, requests DOM snapshot and asks LLM to recover selectors.
"""

import logging
from typing import Dict, Any, Optional, List

from core.interfaces import MCPCommand
from services.llm.generators.llm_generator import LLMGenerator
from services.llm.context.context_builder import ContextBuilder, get_page_context

from .command_pipeline import CommandPipeline

logger = logging.getLogger(__name__)


_FALLBACK_TOOLS = {
    "click", "click_element",
    "fill", "fill_input",
    "press", "press_key",
    "wait_for_selector",
}


class DomFallbackManager:
    """Attempt DOM-based recovery after a tool failure."""

    def __init__(
        self,
        sender,
        session_manager,
        action_feedback,
        login_guard=None,
        login_feedback=None,
        logout_feedback=None,
    ):
        self._sender = sender
        self._session = session_manager
        self._pipeline = CommandPipeline(
            sender=sender,
            action_feedback=action_feedback,
            login_guard=login_guard,
            login_feedback=login_feedback,
            logout_feedback=logout_feedback,
        )
        self._llm = LLMGenerator()
        self._context_builder = ContextBuilder()

    def clear_pending(self, session_id: str):
        if self._session:
            self._session.set_context(session_id, "dom_fallback_pending", None)

    async def maybe_trigger(
        self,
        session_id: str,
        tool_name: Optional[str],
        arguments: Optional[Dict[str, Any]],
        error: Optional[str],
        current_url: str,
        success: bool,
    ) -> bool:
        if success:
            return False
        if tool_name not in _FALLBACK_TOOLS:
            return False
        if not self._session or not self._sender:
            return False

        attempts = self._session.get_context(session_id, "dom_fallback_attempts", 0)
        if attempts >= 1:
            return False

        pending = self._session.get_context(session_id, "dom_fallback_pending")
        if pending:
            return False

        session = self._session.get_session(session_id)
        user_text = _last_user_text(session) if session else ""
        history = session.conversation_history if session else []
        history_len = len(history) if history else 0
        payload = {
            "tool_name": tool_name,
            "arguments": arguments or {},
            "error": error or "",
            "current_url": current_url or "",
            "user_text": user_text,
            "history_len": history_len,
        }
        self._session.set_context(session_id, "dom_fallback_pending", payload)
        self._session.set_context(session_id, "dom_fallback_attempts", attempts + 1)

        await self._sender.send_tts_response(
            session_id,
            "작업 중 오류가 발생하여 재시도 중입니다. 잠시만 기다려 주세요."
        )

        await self._sender.send_tool_calls(
            session_id,
            [MCPCommand(tool_name="get_dom_snapshot", arguments={"include_frames": True})],
        )
        return True

    async def handle_dom_snapshot(
        self,
        session_id: str,
        result: Dict[str, Any],
        current_url: str,
    ) -> bool:
        if not self._session or not self._sender:
            return False

        pending = self._session.get_context(session_id, "dom_fallback_pending")
        if not pending:
            return False

        self._session.set_context(session_id, "dom_fallback_pending", None)
        session = self._session.get_session(session_id)

        # 트리거 이후 새 사용자 입력이 있으면 DOM fallback 무시
        trigger_history_len = pending.get("history_len", 0)
        current_history = session.conversation_history if session else []
        current_user_count = sum(
            1 for m in (current_history or []) if m.get("role") == "user"
        )
        trigger_user_count = sum(
            1 for m in (current_history or [])[:trigger_history_len] if m.get("role") == "user"
        )
        if current_user_count > trigger_user_count:
            logger.info(
                "DOM fallback skipped: new user input detected since trigger "
                "(trigger_users=%d, current_users=%d)",
                trigger_user_count,
                current_user_count,
            )
            return True

        user_text = pending.get("user_text") or _last_user_text(session) or ""
        if not user_text:
            return False

        dom_prompt = _build_dom_prompt(result, pending)
        messages = self._build_messages(
            user_text=user_text,
            current_url=current_url,
            session=session,
            extra_system=dom_prompt,
        )

        llm_result = await self._llm.generate_with_messages(messages, current_url)

        # LLM 응답 전에도 새 사용자 입력 재확인
        current_history_post = session.conversation_history if session else []
        post_user_count = sum(
            1 for m in (current_history_post or []) if m.get("role") == "user"
        )
        if post_user_count > trigger_user_count:
            logger.info(
                "DOM fallback discarded after LLM: new user input during LLM call "
                "(trigger_users=%d, post_llm_users=%d)",
                trigger_user_count,
                post_user_count,
            )
            return True

        commands = self._pipeline.prepare_commands(
            session_id,
            llm_result.commands,
            current_url or ""
        )
        tts_text = await self._pipeline.dispatch(
            session_id,
            commands,
            llm_result.response_text,
            current_url or "",
            lambda: False,
        )
        if tts_text and self._session:
            self._session.add_to_history(session_id, "assistant", tts_text)
        return True

    def _build_messages(
        self,
        user_text: str,
        current_url: str,
        session,
        extra_system: str,
    ) -> List[Dict[str, str]]:
        conversation_history = session.conversation_history if session else None
        session_context = session.context if session else None
        site = None
        try:
            from services.llm.sites.site_manager import get_site_manager
            site = get_site_manager().get_site_by_url(current_url)
        except Exception:
            site = None
        page_context = get_page_context(current_url, site) if current_url else None
        messages = self._context_builder.build_messages(
            user_text=user_text,
            current_url=current_url,
            conversation_history=conversation_history,
            page_context=page_context,
            session_context=session_context,
        )
        messages.insert(1, {"role": "system", "content": extra_system})
        return messages


def _last_user_text(session) -> str:
    if not session:
        return ""
    history = session.conversation_history or []
    for msg in reversed(history):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _build_dom_prompt(result: Dict[str, Any], pending: Dict[str, Any]) -> str:
    dom = (result or {}).get("dom") or ""
    frames = (result or {}).get("frames") or []
    failed_tool = pending.get("tool_name", "")
    failed_args = pending.get("arguments", {})
    error = pending.get("error", "")

    def _truncate(text: str, limit: int = 50000) -> str:
        if not text:
            return ""
        return text if len(text) <= limit else text[:limit]

    frame_lines = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        url = frame.get("url") or ""
        content = frame.get("content") or ""
        frame_lines.append(f"- frame_url: {url}\n{_truncate(content, 20000)}")

    frames_text = "\n".join(frame_lines) if frame_lines else "(no frames)"

    return (
        "## DOM Fallback Context\n"
        f"- failed_tool: {failed_tool}\n"
        f"- failed_args: {failed_args}\n"
        f"- error: {error}\n"
        "## DOM Snapshot (truncated)\n"
        f"{_truncate(dom, 50000)}\n"
        "## Frame Snapshots (truncated)\n"
        f"{frames_text}\n"
        "## Instruction\n"
        "- Use the DOM to find the correct selector and return valid MCP commands.\n"
        "- Prefer stable IDs or unique attributes.\n"
        "- If the element is inside a frame, include frame_url.\n"
    )
