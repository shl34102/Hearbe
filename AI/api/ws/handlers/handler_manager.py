# -*- coding: utf-8 -*-
"""
Handler manager: orchestrates WS handlers and session lifecycle.
"""

import base64
import logging
import os
import time

from core.interfaces import MCPCommand
from services.llm.sites.site_manager import get_current_site, get_page_type
from services.llm.generators.tts_generator import TTSGenerator

from .audio_handler import AudioHandler
from .text_handler import TextHandler
from .mcp_handler import MCPHandler
from .dom_fallback import DomFallbackManager
from .coupang.payment_keypad import PaymentKeypadManager
from .hearbe.hearbe_session_gate import HearbeSessionGate
from .coupang.login_autofill import LoginAutofillManager
from .coupang.login_status import LoginStatusManager
from .coupang.login_challenge import LoginChallengeManager
from .command_queue import CommandQueueManager
from .hearbe.hearbe_signup_b_flow import HearbeSignupBFlowManager
from .hearbe.hearbe_signup_flow import HearbeSignupFlowManager
from .page_extract_manager import PageExtractManager
from .page_focus import PageFocusManager
from .coupang.login_page_state import LoginPageStateManager
from .coupang.order_cancel_flow import CoupangOrderCancelFlowManager
from ..feedback.action_feedback import ActionFeedbackManager
from ..feedback.login_guard import LoginGuard
from ..feedback.login_feedback import LoginFeedbackManager
from ..feedback.logout_feedback import LogoutFeedbackManager
from ..feedback.order_detail_handler import OrderDetailHandler
from ..feedback.hearbe_order_history_handler import HearbeOrderHistoryHandler
from ..feedback.tool_failure_notifier import ToolFailureNotifier
from ..auth.token_manager import TokenManager

logger = logging.getLogger(__name__)


class HandlerManager:
    """Coordinates handlers and shared dependencies."""

    def __init__(
        self,
        asr_service=None,
        nlu_service=None,
        llm_planner=None,
        tts_service=None,
        flow_engine=None,
        session_manager=None,
        sender=None
    ):
        self._sender = sender
        self._session = session_manager
        self._tts = TTSGenerator()
        self._token_manager = TokenManager(sender, session_manager)

        self._command_queue = CommandQueueManager(sender)
        self._page_focus = PageFocusManager(session_manager)
        self._action_feedback = ActionFeedbackManager(sender)
        self._failure_notifier = ToolFailureNotifier(sender)
        self._login_guard = LoginGuard(
            session_manager,
            sender,
            self._action_feedback,
            command_queue=self._command_queue,
        )
        self._login_feedback = LoginFeedbackManager(session_manager, sender)
        self._logout_feedback = LogoutFeedbackManager(session_manager)
        self._dom_fallback = DomFallbackManager(
            sender=sender,
            session_manager=session_manager,
            action_feedback=self._action_feedback,
            login_guard=self._login_guard,
            login_feedback=self._login_feedback,
            logout_feedback=self._logout_feedback,
        )
        self._payment_keypad = PaymentKeypadManager(
            sender=sender,
            session_manager=session_manager,
        )
        self._login_status = LoginStatusManager(
            sender=sender,
            session_manager=session_manager,
        )
        self._login_challenge = LoginChallengeManager(
            sender=sender,
            session_manager=session_manager,
        )
        self._login_page_state = LoginPageStateManager(
            sender=sender,
            session_manager=session_manager,
        )
        self._login_autofill = LoginAutofillManager(
            sender=sender,
            session_manager=session_manager,
            login_feedback=self._login_feedback,
        )
        self._hearbe_signup_b_flow = HearbeSignupBFlowManager(
            sender=sender,
            session_manager=session_manager,
        )
        self._hearbe_signup_flow = HearbeSignupFlowManager(
            sender=sender,
            session_manager=session_manager,
            login_feedback=self._login_feedback,
        )
        self._coupang_order_cancel_flow = CoupangOrderCancelFlowManager(
            sender=sender,
            session_manager=session_manager,
        )
        self._hearbe_session_gate = HearbeSessionGate(
            sender=sender,
            session_manager=session_manager,
        )
        self._order_detail = OrderDetailHandler(
            sender=sender,
            session_manager=session_manager,
            token_manager=self._token_manager,
        )
        self._hearbe_order_history = HearbeOrderHistoryHandler(
            sender=sender,
            session_manager=session_manager,
            token_manager=self._token_manager,
        )
        self._page_extract = PageExtractManager(
            sender=sender,
            session_manager=session_manager,
        )

        self._text_handler = TextHandler(
            nlu_service=nlu_service,
            llm_planner=llm_planner,
            flow_engine=flow_engine,
            session_manager=session_manager,
            sender=sender,
            action_feedback=self._action_feedback,
            login_guard=self._login_guard,
            login_feedback=self._login_feedback,
            hearbe_signup_flow=self._hearbe_signup_flow,
            hearbe_signup_b_flow=self._hearbe_signup_b_flow,
            coupang_order_cancel_flow=self._coupang_order_cancel_flow,
            payment_keypad=self._payment_keypad,
            login_status=self._login_status,
            login_challenge=self._login_challenge,
            login_autofill=self._login_autofill,
            order_detail_handler=self._order_detail,
            page_extract=self._page_extract,
            command_queue=self._command_queue,
            logout_feedback=self._logout_feedback,
        )
        self._login_status.set_enqueue(self._text_handler.enqueue_text)
        self._audio_handler = AudioHandler(
            asr_service=asr_service,
            sender=sender,
            enqueue_text=self._text_handler.enqueue_text
        )
        self._mcp_handler = MCPHandler(
            sender=sender,
            session_manager=session_manager,
            action_feedback=self._action_feedback,
            failure_notifier=self._failure_notifier,
            login_guard=self._login_guard,
            login_feedback=self._login_feedback,
            dom_fallback=self._dom_fallback,
            command_queue=self._command_queue,
        )

    async def create_session(self, session_id: str):
        await self._audio_handler.create_session(session_id)
        await self._text_handler.create_session(session_id)
        self._command_queue.create_session(session_id)

    async def cleanup_session(self, session_id: str):
        await self._audio_handler.cleanup_session(session_id)
        await self._text_handler.cleanup_session(session_id)
        self._command_queue.cleanup_session(session_id)
        self._action_feedback.clear_pending(session_id)
        self._login_guard.clear_pending(session_id)
        self._login_feedback.clear_pending(session_id)
        self._logout_feedback.clear_pending(session_id)
        self._dom_fallback.clear_pending(session_id)
        self._mcp_handler.cleanup_session(session_id)
        self._payment_keypad.cleanup_session(session_id)
        self._login_status.cleanup_session(session_id)
        self._login_challenge.cleanup_session(session_id)
        self._login_page_state.cleanup_session(session_id)
        self._login_autofill.cleanup_session(session_id)
        self._hearbe_signup_b_flow.cleanup_session(session_id)
        self._hearbe_signup_flow.cleanup_session(session_id)
        self._coupang_order_cancel_flow.cleanup_session(session_id)
        self._hearbe_session_gate.cleanup_session(session_id)
        self._order_detail.cleanup_session(session_id)
        self._hearbe_order_history.cleanup_session(session_id)
        self._token_manager.cleanup_session(session_id)

    async def handle_audio_chunk(self, session_id: str, data: dict):
        audio_data = base64.b64decode(data.get("audio", ""))
        seq = data.get("seq", 0)
        is_final = data.get("is_final", False)
        await self._audio_handler.handle_audio_chunk(session_id, audio_data, seq, is_final)

    async def handle_binary_audio(self, session_id: str, data: bytes):
        await self._audio_handler.handle_binary_audio(session_id, data)

    async def handle_user_input(self, session_id: str, data: dict):
        text = data.get("text", "")
        if text.strip():
            logger.info("[INPUT] Text: %s", text.strip())
        await self._text_handler.handle_user_input(session_id, text)

    async def handle_user_confirm(self, session_id: str, data: dict):
        await self._text_handler.handle_user_confirm(session_id, data)

    async def handle_cancel(self, session_id: str):
        await self._audio_handler.clear_audio(session_id)
        await self._text_handler.handle_cancel(session_id)
        self._action_feedback.clear_pending(session_id)
        self._login_guard.clear_pending(session_id)
        self._login_feedback.clear_pending(session_id)
        self._logout_feedback.clear_pending(session_id)
        self._dom_fallback.clear_pending(session_id)
        self._payment_keypad.cleanup_session(session_id)
        self._login_status.cleanup_session(session_id)
        self._login_challenge.cleanup_session(session_id)
        self._login_page_state.cleanup_session(session_id)
        self._login_autofill.cleanup_session(session_id)
        self._hearbe_signup_b_flow.cleanup_session(session_id)
        self._hearbe_signup_flow.cleanup_session(session_id)
        self._coupang_order_cancel_flow.cleanup_session(session_id)
        self._hearbe_session_gate.cleanup_session(session_id)
        self._order_detail.cleanup_session(session_id)
        self._hearbe_order_history.cleanup_session(session_id)
        self._token_manager.cleanup_session(session_id)

    async def handle_interrupt(self, session_id: str):
        await self._audio_handler.clear_audio(session_id)
        await self._text_handler.interrupt(session_id)
        self._command_queue.interrupt(session_id)
        if self._session:
            self._session.set_context(session_id, "interrupt_ts", time.time())
            try:
                suppress_sec = float(os.getenv("TTS_INTERRUPT_SUPPRESS_SEC", "3"))
            except ValueError:
                suppress_sec = 3.0
            self._session.set_context(
                session_id,
                "tts_suppress_until",
                time.time() + suppress_sec
            )
        self._action_feedback.clear_pending(session_id)
        self._login_feedback.clear_pending(session_id)
        self._dom_fallback.clear_pending(session_id)
        self._payment_keypad.cleanup_session(session_id)
        self._login_autofill.cleanup_session(session_id)
        self._login_challenge.cleanup_session(session_id)
        self._login_page_state.cleanup_session(session_id)
        self._hearbe_signup_b_flow.cleanup_session(session_id)
        self._hearbe_signup_flow.cleanup_session(session_id)
        self._coupang_order_cancel_flow.cleanup_session(session_id)
        self._order_detail.cleanup_session(session_id)
        if self._sender:
            await self._sender.cancel_tts(session_id)

    async def handle_mcp_result(self, session_id: str, data: dict):
        tool_name = data.get("tool_name")
        arguments = data.get("arguments") or {}
        if tool_name == "get_user_session" and self._session:
            result = data.get("result") or {}
            if isinstance(result, dict):
                access_token, refresh_token = await self._token_manager.handle_user_session(
                    session_id,
                    data,
                )
                user_id = result.get("user_id") or result.get("userId") or ""
                if user_id:
                    self._session.set_context(session_id, "user_id", str(user_id))
                user_type = result.get("user_type") or result.get("userType") or ""
                if user_type:
                    self._session.set_context(session_id, "user_type", str(user_type))
                logger.info(
                    "get_user_session meta: session=%s user_type=%s user_id=%s",
                    session_id,
                    user_type or "missing",
                    str(user_id) if user_id else "missing",
                )
                self._order_detail.handle_token_update(session_id, access_token, refresh_token)
            else:
                logger.warning(
                    "get_user_session result is not a dict: session=%s type=%s",
                    session_id,
                    type(result),
                )
        await self._command_queue.handle_mcp_result(session_id, tool_name, arguments)
        handled = await self._payment_keypad.handle_mcp_result(session_id, data)
        if handled:
            return
        handled = await self._login_status.handle_mcp_result(session_id, data)
        if handled:
            return
        handled = await self._login_page_state.handle_mcp_result(session_id, data)
        if handled:
            return
        handled = await self._hearbe_session_gate.handle_mcp_result(session_id, data)
        if handled:
            return
        handled = await self._login_autofill.handle_mcp_result(session_id, data)
        if handled:
            return
        handled = await self._coupang_order_cancel_flow.handle_mcp_result(session_id, data)
        if handled:
            return
        handled = await self._order_detail.handle_mcp_result(session_id, data)
        if handled:
            return
        await self._mcp_handler.handle_mcp_result(session_id, data)

    async def handle_page_update(self, session_id: str, data: dict):
        url = data.get("url") or data.get("page_url") or data.get("current_url")
        page_id = data.get("page_id")
        logger.info("handle_page_update: session=%s url=%s page_id=%s", session_id, url, page_id)
        if not url:
            return
        session = self._session.get_session(session_id) if self._session else None
        if not session:
            return
        # Filter noisy PAGE_UPDATEs from background tabs by keeping a per-session "primary" page focus.
        decision = self._page_focus.decide(session_id, url, page_id, session.current_url or "")
        if not decision.accept:
            logger.debug(
                "handle_page_update ignored (not primary): session=%s url=%s page_id=%s primary_page_id=%s primary_host=%s",
                session_id,
                url,
                page_id,
                decision.primary_page_id,
                decision.primary_host,
            )
            return

        previous_url = session.current_url
        if previous_url and previous_url != url:
            self._session.set_context(session_id, "previous_url", previous_url)
        session.current_url = url

        # Announce successful login even when the navigation is observed via
        # page-update (not only via MCP tool result URL changes).
        suppress_login_tts = False
        if self._session:
            until = self._session.get_context(session_id, "tts_suppress_until", 0)
            if until and time.time() < float(until):
                suppress_login_tts = True
        if self._login_feedback and not suppress_login_tts:
            await self._login_feedback.maybe_announce_login_success(session_id, previous_url, url)

        site = get_current_site(url)
        page_type = get_page_type(url)
        logger.info("handle_page_update: site=%s page_type=%s", site.name if site else None, page_type)
        if site:
            session.current_site = site.name
        await self._payment_keypad.handle_page_update(session_id, url)
        await self._login_challenge.handle_page_update(session_id, url)
        await self._order_detail.handle_page_update(session_id, url)
        await self._hearbe_order_history.handle_page_update(session_id, url)
        await self._page_extract.handle_page_update(session_id, url, page_id)
        await self._hearbe_signup_b_flow.handle_page_update(session_id, url)
        await self._hearbe_signup_flow.handle_page_update(session_id, url, previous_url)
        await self._coupang_order_cancel_flow.handle_page_update(session_id, url)

        # On login page entry, trigger autofill probe (no user text required).
        if page_type == "login":
            await self._hearbe_session_gate.handle_login_page_update(session_id, url, previous_url)
            await self._login_autofill.handle_page_update(session_id, url, previous_url)
            await self._login_page_state.handle_page_update(session_id, url, previous_url, page_id)
        # On main page entry, check if user is logged in and redirect to appropriate mall.
        elif page_type == "main":
            # Only on entry (URL change) to avoid repeated session checks / duplicate TTS.
            if previous_url != url:
                await self._hearbe_session_gate.handle_main_page_update(session_id, url)

        # Hearbe: on mall page entry, announce available actions and mall options (cooldown per page_id).
        if (
            site
            and getattr(site, "site_id", "") == "hearbe"
            and page_type == "mall"
            and previous_url != url
            and self._session
        ):
            suppress = False
            until = self._session.get_context(session_id, "tts_suppress_until", 0)
            if until and time.time() < float(until):
                suppress = True

            # Cooldown to avoid repeated guidance during redirect bounces / tab switching.
            # Keyed by page_id so returning to the same mall tab doesn't spam guidance.
            page_key = str(page_id or "none")
            raw = self._session.get_context(session_id, "hearbe_mall_guidance_map", {}) or {}
            guidance_map = raw if isinstance(raw, dict) else {}
            last_ts = guidance_map.get(page_key) or 0.0
            try:
                last_ts = float(last_ts)
            except (TypeError, ValueError):
                last_ts = 0.0

            if not suppress and (time.time() - last_ts) > 300.0:
                guidance_map[page_key] = time.time()
                self._session.set_context(session_id, "hearbe_mall_guidance_map", guidance_map)
                # If /main detected an existing session and redirected here, the session gate
                # intentionally suppresses its own "already logged in" TTS to avoid duplication.
                # We fold that status into this single mall guidance TTS.
                prefix = ""
                try:
                    recent_to = self._session.get_context(session_id, "hearbe_recent_login_redirect_to") or ""
                    recent_ts = float(self._session.get_context(session_id, "hearbe_recent_login_redirect_ts") or 0)
                    recent_reason = self._session.get_context(session_id, "hearbe_recent_login_redirect_reason") or ""
                except Exception:
                    recent_to, recent_ts, recent_reason = "", 0.0, ""

                if recent_reason == "already_logged_in" and recent_to == url and (time.time() - recent_ts) < 10.0:
                    prefix = "이미 로그인되어 있습니다. "
                    self._session.set_context(session_id, "hearbe_recent_login_redirect_to", None)
                    self._session.set_context(session_id, "hearbe_recent_login_redirect_ts", None)
                    self._session.set_context(session_id, "hearbe_recent_login_redirect_reason", None)

                await self._sender.send_tts_response(session_id, prefix + self._tts.build_hearbe_mall_guidance())

    async def handle_invalid_message(self, session_id: str, error: str):
        await self._sender.send_error(session_id, error)
