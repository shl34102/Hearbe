# -*- coding: utf-8 -*-
"""
Text routing orchestrator.
"""

from typing import Optional

from core.interfaces import MCPCommand
from services.llm.rules.product_option import handle_product_option_rule


class TextRouter:
    def __init__(
        self,
        session_manager,
        hearbe_signup_flow,
        hearbe_signup_b_flow,
        coupang_order_cancel_flow,
        payment_keypad,
        login_status,
        login_challenge,
        login_autofill,
        order_detail_handler,
        flow_handler,
        search_query_handler,
        ai_next_router,
        llm_pipeline_handler,
        history_writer,
        interrupt_manager,
        command_pipeline,
        logout_confirm=None,
    ):
        self._session = session_manager
        self._hearbe_signup_flow = hearbe_signup_flow
        self._hearbe_signup_b_flow = hearbe_signup_b_flow
        self._coupang_order_cancel_flow = coupang_order_cancel_flow
        self._payment_keypad = payment_keypad
        self._login_status = login_status
        self._login_challenge = login_challenge
        self._login_autofill = login_autofill
        self._order_detail = order_detail_handler
        self._flow_handler = flow_handler
        self._search_query_handler = search_query_handler
        self._ai_next_router = ai_next_router
        self._llm_pipeline = llm_pipeline_handler
        self._history = history_writer
        self._interrupts = interrupt_manager
        self._command_pipeline = command_pipeline
        self._logout_confirm = logout_confirm

    async def handle_text(self, session_id: str, text: str) -> Optional[str]:
        session = self._session.get_session(session_id) if self._session else None
        if not session:
            return None
        epoch = self._interrupts.get_epoch(session_id)

        if self._hearbe_signup_b_flow:
            handled = await self._hearbe_signup_b_flow.handle_user_text(session_id, text)
            if handled:
                return None

        if self._coupang_order_cancel_flow:
            handled = await self._coupang_order_cancel_flow.handle_user_text(session_id, text)
            if handled:
                return None

        if self._hearbe_signup_flow:
            await self._hearbe_signup_flow.handle_user_text(session_id, text)

        if self._logout_confirm:
            handled = await self._logout_confirm.handle_user_text(session_id, text)
            if handled:
                return None

        if self._payment_keypad:
            handled = await self._payment_keypad.handle_user_text(session_id, text)
            if handled:
                return None

        if self._login_challenge:
            handled = await self._login_challenge.handle_user_text(session_id, text)
            if handled:
                return None

        if self._login_status:
            handled = await self._login_status.handle_user_text(session_id, text)
            if handled:
                return None

        if self._login_autofill:
            handled = await self._login_autofill.handle_user_text(session_id, text)
            if handled:
                return None

        self._history.add_user(session_id, text)

        if self._interrupts.is_interrupted(session_id, epoch):
            return None

        if self._order_detail:
            handled = await self._order_detail.handle_user_text(session_id, text)
            if handled:
                return None

        if self._interrupts.is_interrupted(session_id, epoch):
            return None

        if self._flow_handler and self._flow_handler.is_flow_active(session_id):
            await self._flow_handler.handle_flow_input(session_id, text, session)
            return None

        if self._interrupts.is_interrupted(session_id, epoch):
            return None

        handled = await self._search_query_handler.handle_query(session_id, text, session)
        if handled:
            return None

        if self._interrupts.is_interrupted(session_id, epoch):
            return None

        option_response = handle_product_option_rule(text, session)
        if option_response:
            commands = [
                MCPCommand(tool_name=c.tool_name, arguments=c.arguments, description=c.description)
                for c in option_response.commands
            ]
            commands = self._command_pipeline.prepare_commands(
                session_id,
                commands,
                session.current_url or "",
                allow_extract=True,
            )
            tts_text = await self._command_pipeline.dispatch(
                session_id,
                commands,
                option_response.text,
                session.current_url or "",
                lambda: self._interrupts.is_interrupted(session_id, epoch),
            )
            return tts_text

        if self._ai_next_router:
            ai_next_result = self._ai_next_router.route(text, session.current_url or "")
            if ai_next_result:
                commands = [
                    MCPCommand(tool_name=c.tool_name, arguments=c.arguments, description=c.description)
                    for c in ai_next_result.commands
                ]
                commands = self._command_pipeline.prepare_commands(
                    session_id,
                    commands,
                    session.current_url or "",
                    allow_extract=False,
                )
                tts_text = await self._command_pipeline.dispatch(
                    session_id,
                    commands,
                    ai_next_result.response_text,
                    session.current_url or "",
                    lambda: self._interrupts.is_interrupted(session_id, epoch),
                )
                return tts_text

        if self._interrupts.is_interrupted(session_id, epoch):
            return None

        tts_text = await self._llm_pipeline.handle(
            session_id,
            text,
            session,
            lambda: self._interrupts.is_interrupted(session_id, epoch),
        )
        return tts_text or None
