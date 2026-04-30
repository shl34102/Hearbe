# -*- coding: utf-8 -*-
"""
Command pipeline helpers for LLM/AI-next execution.
"""

import logging
import re
from typing import Optional, Callable, List

from core.interfaces import MCPCommand
from .command_normalizers import normalize_login_phone_commands
from .command_guards import apply_platform_guards

logger = logging.getLogger(__name__)


class CommandPipeline:
    """Prepare and dispatch tool commands with shared safeguards."""

    def __init__(self, sender, action_feedback, login_guard=None, login_feedback=None, logout_feedback=None, command_queue=None):
        self._sender = sender
        self._action_feedback = action_feedback
        self._login_guard = login_guard
        self._login_feedback = login_feedback
        self._logout_feedback = logout_feedback
        self._command_queue = command_queue

    def prepare_commands(
        self,
        session_id: str,
        commands: List,
        current_url: str,
        allow_extract: bool = True,
    ):
        if not commands:
            return commands
        if not allow_extract:
            commands = _filter_extract_commands(commands)
        commands = normalize_login_phone_commands(commands, current_url)
        commands = apply_platform_guards(commands, current_url)
        if current_url and "login" in current_url:
            commands = [
                MCPCommand(
                    tool_name="handle_captcha_modal",
                    arguments={},
                    description="handle captcha modal if present",
                )
            ] + commands
        if self._login_feedback:
            self._login_feedback.mark_login_submit_pending(
                session_id,
                commands,
                current_url or ""
            )
        if self._logout_feedback:
            self._logout_feedback.mark_logout_pending(
                session_id,
                commands,
                current_url or "",
            )
        return commands

    async def dispatch(
        self,
        session_id: str,
        commands: List,
        response_text: str,
        current_url: str,
        interrupted: Callable[[], bool],
    ) -> Optional[str]:
        """
        Send tool calls and TTS response if applicable.

        Returns the TTS text that was sent (if any).
        """
        if self._command_queue:
            if interrupted():
                return None

            if _should_interrupt_for_order_detail(commands):
                self._command_queue.interrupt(session_id)

            if not commands:
                return await self._command_queue.enqueue_batch(
                    session_id,
                    [],
                    response_text,
                    current_url,
                    interrupted,
                    wait=True,
                )

            guard_commands = None
            if self._login_guard:
                guard_commands = self._login_guard.prepare_guard(
                    session_id,
                    commands,
                    response_text,
                    current_url or ""
                )
            if guard_commands:
                return await self._command_queue.enqueue_batch(
                    session_id,
                    guard_commands,
                    "",
                    current_url,
                    interrupted,
                    wait=True,
                )

            pending_msg = self._action_feedback.register_commands(
                session_id,
                commands,
                current_url or ""
            )
            response_text = pending_msg or response_text

            return await self._command_queue.enqueue_batch(
                session_id,
                commands,
                response_text,
                current_url,
                interrupted,
                wait=True,
            )

        if not commands:
            return await self._send_response(session_id, response_text, interrupted)

        if interrupted():
            return None

        guard_commands = None
        if self._login_guard:
            guard_commands = self._login_guard.prepare_guard(
                session_id,
                commands,
                response_text,
                current_url or ""
            )
        if guard_commands:
            await self._sender.send_tool_calls(session_id, guard_commands)
            return None

        await self._sender.send_tool_calls(session_id, commands)

        pending_msg = self._action_feedback.register_commands(
            session_id,
            commands,
            current_url or ""
        )
        if pending_msg:
            return await self._send_response(session_id, pending_msg, interrupted)
        return await self._send_response(session_id, response_text, interrupted)

    async def _send_response(
        self,
        session_id: str,
        response_text: str,
        interrupted: Callable[[], bool],
    ) -> Optional[str]:
        if not response_text:
            return None
        if interrupted():
            return None
        logger.info(f"Sending TTS response: '{response_text[:80]}...'")
        await self._sender.send_tts_response(session_id, response_text)
        return response_text


def _filter_extract_commands(commands: List) -> List:
    filtered = []
    removed = 0
    for cmd in commands:
        tool_name = getattr(cmd, "tool_name", "") or ""
        if tool_name.startswith("extract"):
            removed += 1
            continue
        filtered.append(cmd)
    if removed:
        logger.info("Filtered %d extract command(s) from LLM output", removed)
    return filtered


def _should_interrupt_for_order_detail(commands: List) -> bool:
    for cmd in commands or []:
        tool_name = getattr(cmd, "tool_name", "") or ""
        if tool_name != "goto":
            continue
        args = getattr(cmd, "arguments", None) or {}
        url = str(args.get("url") or "")
        if not url:
            continue
        if re.search(r"/ssr/desktop/order/\d+/?$", url):
            return True
    return False
