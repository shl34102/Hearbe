# -*- coding: utf-8 -*-
"""
Login guard for protected actions (add to cart / buy now).

Runs a lightweight login check before executing sensitive commands.
"""

from dataclasses import dataclass
from typing import Optional, List

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_selector


@dataclass
class PendingLoginAction:
    commands: List[MCPCommand]
    response_text: str
    action_type: str


class LoginGuard:
    """Defers protected actions until login status is checked."""

    def __init__(self, session_manager, sender, action_feedback, command_queue=None):
        self._session = session_manager
        self._sender = sender
        self._action_feedback = action_feedback
        self._command_queue = command_queue

    def prepare_guard(self, session_id: str, commands: List[MCPCommand], response_text: str, current_url: str) -> Optional[List[MCPCommand]]:
        if not commands:
            return None
        if not self._requires_login_guard(commands, current_url):
            return None

        if self._session:
            self._session.set_context(
                session_id,
                "pending_login_action",
                PendingLoginAction(
                    commands=commands,
                    response_text=response_text or "",
                    action_type="protected_action"
                )
            )

        return [
            MCPCommand(
                tool_name="check_login_status",
                arguments={},
                description="check login status before protected action"
            )
        ]

    async def handle_login_check_result(self, session_id: str, result: dict, current_url: str) -> bool:
        if not self._session:
            return False

        pending: PendingLoginAction = self._session.get_context(session_id, "pending_login_action")
        if not pending:
            return False

        logged_in = result.get("logged_in")

        # Unknown -> proceed with original commands
        if logged_in is None or logged_in is True:
            pending_msg = self._action_feedback.register_commands(
                session_id,
                pending.commands,
                current_url or ""
            )
            response_text = pending_msg or pending.response_text
            if self._command_queue:
                await self._command_queue.enqueue_batch(
                    session_id,
                    pending.commands,
                    response_text,
                    current_url or "",
                    front=True,
                    wait=False,
                )
            else:
                await self._sender.send_tool_calls(session_id, pending.commands)
                if response_text:
                    await self._sender.send_tts_response(session_id, response_text)
            self._session.set_context(session_id, "pending_login_action", None)
            return True

        # Not logged in -> prompt user to login/signup
        if logged_in is False:
            await self._sender.send_tts_response(
                session_id,
                "로그인이 필요합니다. 회원이시면 로그인, 아니면 회원가입을 도와드릴까요?"
            )
            self._session.set_context(session_id, "pending_login_action", None)
            return True

        return False

    def clear_pending(self, session_id: str):
        if self._session:
            self._session.set_context(session_id, "pending_login_action", None)

    def _requires_login_guard(self, commands: List[MCPCommand], current_url: str) -> bool:
        add_to_cart_selector = get_selector(current_url, "add_to_cart") if current_url else None
        buy_now_selector = get_selector(current_url, "buy_now") if current_url else None

        for cmd in commands:
            tool = cmd.tool_name
            args = cmd.arguments or {}
            if tool in ("click", "click_element"):
                selector = args.get("selector") or ""
                if add_to_cart_selector and selector == add_to_cart_selector:
                    return True
                if buy_now_selector and selector == buy_now_selector:
                    return True
            if tool == "click_text":
                text = (args.get("text") or "")
                if any(keyword in text for keyword in ("장바구니", "바로구매", "구매하기")):
                    return True
        return False
