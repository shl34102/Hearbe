# -*- coding: utf-8 -*-
"""
Text handler: user_input -> NLU/LLM/Flow -> TTS/tool_calls

Coordinates text processing pipeline and delegates to specialized handlers.
"""

import asyncio
import logging
import re
from typing import Dict, Any

from core.interfaces import ASRResult
from core.korean_numbers import extract_ordinal_index
from .search_query_handler import SearchQueryHandler
from .command_pipeline import CommandPipeline
from .text_ingress.text_queue import TextQueueManager
from .text_processing.flow_handler import FlowHandler
from .text_processing.llm_pipeline_handler import LLMPipelineHandler
from .text_routing.ai_next_router import AiNextRouter
from .text_routing.text_router import TextRouter
from .text_session.history_writer import HistoryWriter
from .text_session.interrupt_manager import InterruptManager
from .logout_confirm import LogoutConfirmManager
from services.llm.sites.site_manager import get_page_type

logger = logging.getLogger(__name__)


_SEARCH_SELECT_HINTS = ("선택", "열어", "클릭", "눌러", "골라", "고르")
_SEARCH_READ_HINTS = ("읽어", "들려", "보여", "요약")

_BARE_ORDINAL_RE = re.compile(r"^\\s*[가-힣0-9]+\\s*(?:번째|번)\\s*(?:상품)?\\s*(?:이요|요)?\\s*$")


def _is_bare_ordinal_utterance(text: str) -> bool:
    """
    True only for short ordinal-only utterances like "1번", "첫번째", "2번이요".
    """
    if not text:
        return False
    if extract_ordinal_index(text) is None:
        return False
    return bool(_BARE_ORDINAL_RE.match(text))


def _is_search_quick_select(text: str) -> bool:
    """
    Detect selection requests that should not be blocked by auto-extract.

    When the user is on a search page and asks to select an item (e.g., "1번 선택"),
    we can click by selector without needing extracted search_results first. In that
    case, forcing ensure_context would trigger auto-announce TTS and delay the action.
    """
    value = (text or "").strip()
    if not value:
        return False
    if any(hint in value for hint in _SEARCH_READ_HINTS):
        return False
    if any(hint in value for hint in _SEARCH_SELECT_HINTS):
        return True
    if _is_bare_ordinal_utterance(value):
        return True
    return False


class TextHandler:
    """
    Handles text input pipeline and flow steps.

    Responsibilities:
    - Queue/worker management for text inputs
    - Routing to appropriate handlers (Flow, Search, LLM)
    - Coordinating NLU/LLM pipeline
    """

    def __init__(
        self,
        nlu_service,
        llm_planner,
        flow_engine,
        session_manager,
        sender,
        action_feedback,
        login_guard=None,
        login_feedback=None,
        hearbe_signup_flow=None,
        hearbe_signup_b_flow=None,
        coupang_order_cancel_flow=None,
        payment_keypad=None,
        login_status=None,
        login_challenge=None,
        login_autofill=None,
        order_detail_handler=None,
        page_extract=None,
        command_queue=None,
        logout_feedback=None,
    ):
        self._nlu = nlu_service
        self._llm = llm_planner
        self._flow = flow_engine
        self._session = session_manager
        self._sender = sender
        self._action_feedback = action_feedback
        self._login_guard = login_guard
        self._login_feedback = login_feedback
        self._hearbe_signup_flow = hearbe_signup_flow
        self._hearbe_signup_b_flow = hearbe_signup_b_flow
        self._coupang_order_cancel_flow = coupang_order_cancel_flow
        self._payment_keypad = payment_keypad
        self._login_status = login_status
        self._login_challenge = login_challenge
        self._login_autofill = login_autofill
        self._order_detail = order_detail_handler
        self._page_extract = page_extract
        self._command_pipeline = CommandPipeline(
            sender=sender,
            action_feedback=action_feedback,
            login_guard=login_guard,
            login_feedback=login_feedback,
            logout_feedback=logout_feedback,
            command_queue=command_queue,
        )
        self._logout_confirm = LogoutConfirmManager(
            sender=sender,
            session_manager=session_manager,
            command_pipeline=self._command_pipeline,
        )

        # Specialized handlers
        self._search_query_handler = SearchQueryHandler(session_manager, sender)

        # Queue management
        self._text_tasks: Dict[str, asyncio.Task] = {}
        self._queue_manager = TextQueueManager()
        self._interrupts = InterruptManager()
        self._history = HistoryWriter(session_manager)
        self._flow_handler = FlowHandler(flow_engine, sender)
        self._llm_pipeline = LLMPipelineHandler(
            nlu_service=nlu_service,
            llm_planner=llm_planner,
            flow_engine=flow_engine,
            sender=sender,
            command_pipeline=self._command_pipeline,
        )
        self._ai_next_router = AiNextRouter()
        self._text_router = TextRouter(
            session_manager=session_manager,
            hearbe_signup_flow=hearbe_signup_flow,
            hearbe_signup_b_flow=hearbe_signup_b_flow,
            coupang_order_cancel_flow=coupang_order_cancel_flow,
            payment_keypad=payment_keypad,
            login_status=login_status,
            login_challenge=login_challenge,
            login_autofill=login_autofill,
            order_detail_handler=order_detail_handler,
            flow_handler=self._flow_handler,
            search_query_handler=self._search_query_handler,
            ai_next_router=self._ai_next_router,
            llm_pipeline_handler=self._llm_pipeline,
            history_writer=self._history,
            interrupt_manager=self._interrupts,
            command_pipeline=self._command_pipeline,
            logout_confirm=self._logout_confirm,
        )

    async def create_session(self, session_id: str):
        """Create text processing queue and worker for session."""
        self._queue_manager.create_session(session_id)
        self._interrupts.create_session(session_id)
        self._text_tasks[session_id] = asyncio.create_task(self._text_worker(session_id))

    async def cleanup_session(self, session_id: str):
        """Clean up session resources."""
        task = self._text_tasks.pop(session_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._queue_manager.cleanup_session(session_id)
        self._interrupts.cleanup_session(session_id)
        self._logout_confirm.cleanup_session(session_id)

    async def interrupt(self, session_id: str):
        """Interrupt current processing and prioritize new input."""
        self._interrupts.interrupt(session_id)
        self._queue_manager.interrupt(session_id)

        session = self._session.get_session(session_id) if self._session else None
        if session and self._flow and self._flow.is_flow_active(session_id):
            await self._flow.cancel_flow(session)

    async def handle_user_input(self, session_id: str, text: str):
        """Handle text input from user."""
        result = ASRResult(
            text=text,
            confidence=1.0,
            language="ko",
            duration=0.0,
            is_final=True,
            segment_id="text_input"
        )
        await self._sender.send_asr_result(session_id, result)
        await self.enqueue_text(session_id, text)

    async def handle_user_confirm(self, session_id: str, data: Dict[str, Any]):
        """Handle user confirmation (yes/no)."""
        confirmed = data.get("confirmed", False)
        await self.enqueue_text(session_id, "yes" if confirmed else "no")

    async def handle_cancel(self, session_id: str):
        """Handle cancellation request."""
        session = self._session.get_session(session_id) if self._session else None
        if session and self._flow:
            await self._flow.cancel_flow(session)
        self._logout_confirm.cleanup_session(session_id)

        await self._sender.send_status(session_id, "cancelled", "Cancelled")
        await self._sender.send_tts_response(session_id, "Cancelled")

    async def enqueue_text(self, session_id: str, text: str):
        """Enqueue text for processing."""
        self._queue_manager.enqueue_text(session_id, text)

    async def _text_worker(self, session_id: str):
        """Background worker that processes queued text inputs."""
        queue = self._queue_manager.get_queue(session_id)
        if not queue:
            return

        logger.debug(f"Text worker started: {session_id}")
        try:
            while True:
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    continue
                self._queue_manager.mark_dequeued(session_id, text)
                await self._process_text_input(session_id, text)
        except asyncio.CancelledError:
            logger.debug(f"Text worker cancelled: {session_id}")
        except Exception as e:
            logger.error(f"Text worker error: {session_id}: {e}")

    async def _process_text_input(self, session_id: str, text: str):
        """
        Process text input through the routing pipeline.
        """
        try:
            session = self._session.get_session(session_id) if self._session else None
            if session and self._order_detail:
                triggered = await self._order_detail.ensure_context(
                    session_id,
                    session.current_url,
                    session,
                )
                if triggered:
                    retries = 0
                    if self._session:
                        retries = self._session.get_context(session_id, "auto_extract_retry", 0)
                    if retries < 1:
                        if self._session:
                            self._session.set_context(session_id, "auto_extract_retry", retries + 1)
                        asyncio.create_task(self._requeue_after_delay(session_id, text, delay_sec=1.6))
                        return
                    if self._session:
                        self._session.set_context(session_id, "auto_extract_retry", 0)

            if session and self._page_extract:
                page_type = get_page_type(session.current_url or "")
                skip_auto_extract = page_type == "search" and _is_search_quick_select(text)
                if not skip_auto_extract:
                    triggered = await self._page_extract.ensure_context(
                        session_id,
                        session.current_url,
                        session
                    )
                    if triggered:
                        retries = 0
                        if self._session:
                            retries = self._session.get_context(session_id, "auto_extract_retry", 0)
                        if retries < 1:
                            if self._session:
                                self._session.set_context(session_id, "auto_extract_retry", retries + 1)
                            asyncio.create_task(self._requeue_after_delay(session_id, text, delay_sec=1.6))
                            return
                        if self._session:
                            self._session.set_context(session_id, "auto_extract_retry", 0)

            if self._session:
                self._session.set_context(session_id, "auto_extract_retry", 0)

            tts_text = await self._text_router.handle_text(session_id, text)
            if tts_text:
                self._history.add_assistant(session_id, tts_text)
        except Exception as e:
            logger.error(f"Text processing failed: {e}")
            await self._sender.send_error(session_id, "Processing error")

    async def _requeue_after_delay(self, session_id: str, text: str, delay_sec: float) -> None:
        try:
            await asyncio.sleep(delay_sec)
            await self.enqueue_text(session_id, text)
        except Exception:
            return
