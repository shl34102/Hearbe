# -*- coding: utf-8 -*-
"""
Action feedback manager

Tracks actions that require confirmation and adjusts TTS to avoid
overstating success when the real outcome is unknown.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, List, Any

from services.llm.sites.site_manager import get_selector, get_page_type, get_site_manager
from core.interfaces import MCPCommand
from ..utils.temp_file_manager import TempFileManager

logger = logging.getLogger(__name__)


# Messages (keep ASCII via unicode escapes)
MSG_ADD_TO_CART_PENDING = "\uc7a5\ubc14\uad6c\ub2c8 \ub2f4\uae30\ub97c \uc2dc\ub3c4\ud569\ub2c8\ub2e4. \uacb0\uacfc\ub97c \ud655\uc778 \uc911\uc785\ub2c8\ub2e4."
MSG_GO_TO_CART = "\uc7a5\ubc14\uad6c\ub2c8\ub85c \uc774\ub3d9\ud569\ub2c8\ub2e4."
MSG_CHECKOUT_PENDING = "\uacb0\uc81c\ub97c \uc2dc\ub3c4\ud569\ub2c8\ub2e4. \uc7a0\uc2dc\ub9cc \uae30\ub2e4\ub824 \uc8fc\uc138\uc694."
MSG_CART_VERIFY_MOVE = "\uc7a5\ubc14\uad6c\ub2c8 \ubc18\uc601 \uc5ec\ubd80\ub97c \ud655\uc778\ud558\uae30 \uc704\ud574 \uc7a5\ubc14\uad6c\ub2c8\ub85c \uc774\ub3d9\ud569\ub2c8\ub2e4."
MSG_CART_VERIFY_SUCCESS = "\uc7a5\ubc14\uad6c\ub2c8\uc5d0\uc11c \uc0c1\ud488\uc774 \ud655\uc778\ub418\uc5c8\uc2b5\ub2c8\ub2e4."
MSG_CART_VERIFY_FAIL = "\uc7a5\ubc14\uad6c\ub2c8\uc5d0\uc11c \uc0c1\ud488\uc774 \ud655\uc778\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4."
MSG_ADD_TO_CART_CLICK_FAIL = "\uc7a5\ubc14\uad6c\ub2c8 \ub2f4\uae30 \ubc84\ud2bc \ud074\ub9ad\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \uc2dc\ub3c4\ud574 \uc8fc\uc138\uc694."
MSG_CHECKOUT_CLICK_FAIL = "\uacb0\uc81c \ubc84\ud2bc \ud074\ub9ad\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \uc2dc\ub3c4\ud574 \uc8fc\uc138\uc694."
MSG_ADD_TO_CART_NEEDS_MANUAL = "\ubc84\ud2bc \ud074\ub9ad\uc740 \uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4. \uc7a5\ubc14\uad6c\ub2c8 \ubc18\uc601\uc740 \uc218\ub3d9 \ud655\uc778\uc774 \ud544\uc694\ud569\ub2c8\ub2e4."

TEXT_CART = "\uc7a5\ubc14\uad6c\ub2c8"
TEXT_ADD_TO_CART = "\uc7a5\ubc14\uad6c\ub2c8 \ub2f4\uae30"
CHECKOUT_KEYWORDS = ("\uad6c\ub9e4\ud558\uae30", "\uacb0\uc81c", "\uc8fc\ubb38\ud558\uae30")


@dataclass
class PendingAction:
    """Pending action requiring confirmation."""

    action_type: str
    selector: Optional[str]
    tool_name: str
    current_url: Optional[str] = None


class ActionFeedbackManager:
    """Tracks pending actions and emits safer feedback."""

    def __init__(self, sender):
        self._sender = sender
        self._pending: Dict[str, PendingAction] = {}
        self._file_manager = TempFileManager()

    def register_commands(self, session_id: str, commands: List, current_url: str) -> Optional[str]:
        """
        Inspect commands and register pending actions that need confirmation.

        Returns:
            Optional processing message to speak immediately.
        """
        if not commands:
            return None

        selector = get_selector(current_url, "add_to_cart") if current_url else None
        checkout_selector = get_selector(current_url, "checkout_button") if current_url else None
        is_cart_page = bool(current_url and get_page_type(current_url) == "cart")

        cart_url = None
        if current_url:
            site = get_site_manager().get_site_by_url(current_url)
            if site:
                cart_url = site.get_url("cart")
        is_go_to_cart = False
        if cart_url:
            for cmd in commands:
                if cmd.tool_name == "goto" and (cmd.arguments or {}).get("url") == cart_url:
                    is_go_to_cart = True
                    break

        saw_cart_click = False
        for cmd in commands:
            tool = cmd.tool_name
            args = cmd.arguments or {}

            if tool in ("click", "click_element"):
                if selector and args.get("selector") == selector:
                    self._pending[session_id] = PendingAction(
                        action_type="add_to_cart",
                        selector=selector,
                        tool_name=tool,
                        current_url=current_url,
                    )
                    return MSG_ADD_TO_CART_PENDING
                if is_cart_page and checkout_selector and args.get("selector") == checkout_selector:
                    self._pending[session_id] = PendingAction(
                        action_type="checkout",
                        selector=checkout_selector,
                        tool_name=tool,
                        current_url=current_url,
                    )
                    return MSG_CHECKOUT_PENDING

            if tool == "click_text":
                text = (args.get("text") or "").strip()
                if text == TEXT_CART:
                    saw_cart_click = True
                if text == TEXT_ADD_TO_CART:
                    self._pending[session_id] = PendingAction(
                        action_type="add_to_cart",
                        selector=None,
                        tool_name=tool,
                        current_url=current_url,
                    )
                    return MSG_ADD_TO_CART_PENDING
                if is_cart_page and any(keyword in text for keyword in CHECKOUT_KEYWORDS):
                    self._pending[session_id] = PendingAction(
                        action_type="checkout",
                        selector=None,
                        tool_name=tool,
                        current_url=current_url,
                    )
                    return MSG_CHECKOUT_PENDING

        if saw_cart_click or is_go_to_cart:
            return MSG_GO_TO_CART

        return None

    async def handle_mcp_result(
        self,
        session_id: str,
        tool_name: Optional[str],
        arguments: Optional[dict],
        success: bool,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Handle MCP tool result to emit confirmation-safe feedback."""
        pending = self._pending.get(session_id)
        if not pending:
            return False

        # Verification phase: check cart contents after navigation/extract
        if pending.action_type == "add_to_cart_verify":
            if tool_name == "extract_cart":
                products = (result or {}).get("cart_items") or []
                self._file_manager.save_json(
                    data={
                        "success": success,
                        "products": products,
                        "page_url": (result or {}).get("page_url"),
                    },
                    session_id=session_id,
                    category="cart_verify",
                    filename_prefix="cart_verify",
                )
                if success and products:
                    await self._sender.send_tts_response(session_id, MSG_CART_VERIFY_SUCCESS)
                else:
                    await self._sender.send_tts_response(session_id, MSG_CART_VERIFY_FAIL)
                self._pending.pop(session_id, None)
                return True
            return False

        if pending.action_type == "checkout_verify":
            if tool_name == "extract_cart":
                self._pending.pop(session_id, None)
                return True
            return False

        if tool_name not in ("click", "click_element", "click_text"):
            return False

        if pending.selector:
            if not arguments or arguments.get("selector") != pending.selector:
                return False

        if not success:
            msg = MSG_ADD_TO_CART_CLICK_FAIL
            if pending.action_type == "checkout":
                msg = MSG_CHECKOUT_CLICK_FAIL
            await self._sender.send_tts_response(session_id, msg)
            self._pending.pop(session_id, None)
            return True

        if pending.action_type == "checkout":
            verify_commands = self._build_verify_checkout_commands(pending.current_url or "")
            if verify_commands:
                await self._sender.send_tool_calls(session_id, verify_commands)
                self._pending[session_id] = PendingAction(
                    action_type="checkout_verify",
                    selector=None,
                    tool_name="extract_cart",
                    current_url=pending.current_url,
                )
                return True
            self._pending.pop(session_id, None)
            return True

        verify_commands = self._build_verify_add_to_cart_commands(pending.current_url or "")
        if verify_commands:
            await self._sender.send_tts_response(session_id, MSG_CART_VERIFY_MOVE)
            await self._sender.send_tool_calls(session_id, verify_commands)
            self._pending[session_id] = PendingAction(
                action_type="add_to_cart_verify",
                selector=None,
                tool_name="extract_cart",
                current_url=pending.current_url,
            )
            return True

        await self._sender.send_tts_response(session_id, MSG_ADD_TO_CART_NEEDS_MANUAL)
        self._pending.pop(session_id, None)
        return True

    def _build_verify_add_to_cart_commands(self, current_url: str) -> List[MCPCommand]:
        site = get_site_manager().get_site_by_url(current_url)
        if not site:
            return []

        cart_url = site.get_url("cart")
        if not cart_url:
            return []

        return [
            MCPCommand(
                tool_name="goto",
                arguments={"url": cart_url},
                description="Go to cart page",
            ),
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 1500},
                description="Wait for cart page load",
            ),
            MCPCommand(
                tool_name="extract_cart",
                arguments={},
                description="Extract cart items",
            ),
        ]

    def _build_verify_checkout_commands(self, current_url: str) -> List[MCPCommand]:
        # We intentionally do not auto-verify checkout via `extract_cart`.
        # After clicking the cart checkout button, the browser usually navigates to
        # `checkout.coupang.com/...`, which should be handled by page-update flows
        # (and extractors) rather than forcing another cart extract.
        if not current_url or get_page_type(current_url) != "cart":
            return []
        return []

    def clear_pending(self, session_id: str):
        """Clear pending actions for a session."""
        self._pending.pop(session_id, None)

    def get_pending_action(self, session_id: str) -> Optional[PendingAction]:
        """
        Introspection helper for other handlers (e.g., MCP result handler).

        We use this to adjust downstream behavior (like suppressing verbose TTS)
        while a verification flow is in progress.
        """

        return self._pending.get(session_id)

    def get_pending_action_type(self, session_id: str) -> Optional[str]:
        pending = self._pending.get(session_id)
        return pending.action_type if pending else None
