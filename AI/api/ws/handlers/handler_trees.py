# -*- coding: utf-8 -*-
"""
Site-specific handler trees.
"""

from __future__ import annotations

from typing import Optional

from services.llm.sites.site_manager import get_page_type

from .hearbe.hearbe_session_gate import HearbeSessionGate
from .hearbe.hearbe_signup_b_flow import HearbeSignupBFlowManager
from .hearbe.hearbe_signup_flow import HearbeSignupFlowManager
from .coupang.login_autofill import LoginAutofillManager
from .coupang.login_challenge import LoginChallengeManager
from .coupang.login_page_state import LoginPageStateManager
from .coupang.login_status import LoginStatusManager
from .coupang.payment_keypad import PaymentKeypadManager
from ..feedback.hearbe_order_history_handler import HearbeOrderHistoryHandler


class CoupangHandlerTree:
    def __init__(self, sender, session_manager, login_feedback=None):
        self.payment_keypad = PaymentKeypadManager(
            sender=sender,
            session_manager=session_manager,
        )
        self.login_status = LoginStatusManager(
            sender=sender,
            session_manager=session_manager,
        )
        self.login_challenge = LoginChallengeManager(
            sender=sender,
            session_manager=session_manager,
        )
        self.login_page_state = LoginPageStateManager(
            sender=sender,
            session_manager=session_manager,
        )
        self.login_autofill = LoginAutofillManager(
            sender=sender,
            session_manager=session_manager,
            login_feedback=login_feedback,
        )

    async def handle_page_update(
        self,
        session_id: str,
        url: str,
        previous_url: Optional[str] = None,
        page_id: Optional[str] = None,
    ) -> None:
        await self.payment_keypad.handle_page_update(session_id, url)
        await self.login_challenge.handle_page_update(session_id, url)

        if get_page_type(url) == "login":
            await self.login_autofill.handle_page_update(session_id, url, previous_url)
            await self.login_page_state.handle_page_update(session_id, url, previous_url, page_id)

    async def handle_mcp_result(self, session_id: str, data: dict) -> bool:
        handled = await self.payment_keypad.handle_mcp_result(session_id, data)
        if handled:
            return True
        handled = await self.login_status.handle_mcp_result(session_id, data)
        if handled:
            return True
        handled = await self.login_page_state.handle_mcp_result(session_id, data)
        if handled:
            return True
        handled = await self.login_autofill.handle_mcp_result(session_id, data)
        if handled:
            return True
        return False

    def cleanup_session(self, session_id: str) -> None:
        self.payment_keypad.cleanup_session(session_id)
        self.login_status.cleanup_session(session_id)
        self.login_challenge.cleanup_session(session_id)
        self.login_page_state.cleanup_session(session_id)
        self.login_autofill.cleanup_session(session_id)


class HearbeHandlerTree:
    def __init__(self, sender, session_manager, login_feedback=None, token_manager=None):
        self.session_gate = HearbeSessionGate(
            sender=sender,
            session_manager=session_manager,
        )
        self.signup_b_flow = HearbeSignupBFlowManager(
            sender=sender,
            session_manager=session_manager,
        )
        self.signup_flow = HearbeSignupFlowManager(
            sender=sender,
            session_manager=session_manager,
            login_feedback=login_feedback,
        )
        self.order_history = HearbeOrderHistoryHandler(
            sender=sender,
            session_manager=session_manager,
            token_manager=token_manager,
        )

    async def handle_page_update(
        self,
        session_id: str,
        url: str,
        previous_url: Optional[str] = None,
        page_id: Optional[str] = None,
    ) -> None:
        await self.order_history.handle_page_update(session_id, url)
        await self.signup_b_flow.handle_page_update(session_id, url)
        handled_signup = await self.signup_flow.handle_page_update(session_id, url, previous_url)

        page_type = get_page_type(url)
        if page_type == "login" and not handled_signup:
            await self.session_gate.handle_login_page_update(session_id, url, previous_url)
        elif page_type == "main" and previous_url != url:
            await self.session_gate.handle_main_page_update(session_id, url)

    async def handle_mcp_result(self, session_id: str, data: dict) -> bool:
        return await self.session_gate.handle_mcp_result(session_id, data)

    def cleanup_session(self, session_id: str) -> None:
        self.signup_b_flow.cleanup_session(session_id)
        self.signup_flow.cleanup_session(session_id)
        self.session_gate.cleanup_session(session_id)
        self.order_history.cleanup_session(session_id)


__all__ = ["CoupangHandlerTree", "HearbeHandlerTree"]
