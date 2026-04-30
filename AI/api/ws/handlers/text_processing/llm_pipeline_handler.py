# -*- coding: utf-8 -*-
"""
NLU/LLM pipeline handler.
"""

import asyncio
import logging
import time

from core.interfaces import IntentType
from core.korean_numbers import extract_ordinal_index
from services.llm.planner.selection.option_select import coerce_option_clicks, is_option_request
from services.llm.feedback.fast_ack import FastAckGenerator
from services.llm.generators.tts_text_generator import TTSTextGenerator
from services.llm.sites.site_manager import get_page_type, get_selector
from services.llm.pipelines.compound import handle_read_then_act
from services.llm.pipelines.read import (
    handle_product_info_read,
    handle_page_info_read,
    handle_cart_summary_read,
    handle_order_list_summary_read,
    handle_search_summary_read,
)
from services.llm.pipelines.read.product_info import (
    has_recent_product_detail,
    is_product_info_request,
)

logger = logging.getLogger(__name__)


class LLMPipelineHandler:
    def __init__(self, nlu_service, llm_planner, flow_engine, sender, command_pipeline):
        self._nlu = nlu_service
        self._llm = llm_planner
        self._flow = flow_engine
        self._sender = sender
        self._command_pipeline = command_pipeline
        self._fast_ack = FastAckGenerator()
        self._tts_only = TTSTextGenerator()

    async def handle(self, session_id: str, text: str, session, interrupted) -> str:
        """
        Handle text through NLU/LLM pipeline.

        Returns the TTS text that was sent (if any).
        """
        if interrupted():
            return ""
        intent = None
        resolved_text = text

        # NLU processing
        if self._nlu:
            context = session.context
            intent = await self._nlu.analyze_intent(text, context)
            resolved_text = await self._nlu.resolve_reference(text, context)

        # Debugging: track what text the planner actually sees and how ordinals are parsed.
        # We only log when reference resolution changed text or when an ordinal is detected,
        # to avoid spamming logs for every utterance.
        ordinal_idx = extract_ordinal_index(resolved_text)
        if resolved_text != text or ordinal_idx is not None:
            logger.info(
                "Input normalized: session=%s raw_text='%s' resolved_text='%s' ordinal_index=%s",
                session_id,
                (text or "")[:200],
                (resolved_text or "")[:200],
                ordinal_idx,
            )

        if not self._llm:
            return ""

        compound_read_sent = False

        # Read-only pipelines: bypass command LLM and generate TTS directly.
        if session and session.context:
            current_url = session.current_url or ""
            page_type = get_page_type(current_url) if current_url else None

            # Product info requests may arrive before extract finishes on product pages.
            # Guard by page_type to avoid misfiring on non-product pages (e.g., "현재 페이지 정보").
            if page_type == "product" and is_product_info_request(resolved_text):
                waited = await self._wait_for_product_detail(session, session_id, interrupted)
                if not waited and not has_recent_product_detail(session):
                    pending = session.context.get("pending_product_info_read")
                    if not pending:
                        session.context["pending_product_info_read"] = {
                            "text": resolved_text,
                            "ts": time.time(),
                        }
                    if not interrupted():
                        ack_text = "상품 정보를 불러오는 중이에요. 잠시만 기다려 주세요."
                        await self._sender.send_tts_response(session_id, ack_text)
                        return ack_text
            read_handlers = (
                handle_page_info_read,
                handle_product_info_read,
                handle_cart_summary_read,
                handle_order_list_summary_read,
                handle_search_summary_read,
            )
            compound_result = handle_read_then_act(resolved_text, session, read_handlers)
            if compound_result:
                compound_response, handler_name = compound_result
                logger.info(
                    "Read pipeline hit (compound): handler=%s session=%s",
                    handler_name,
                    session_id,
                )
                # Avoid LLM TTS asking for confirmation when actions will run.
                await self._sender.send_tts_response(session_id, compound_response.text)
                compound_read_sent = True

            if not compound_read_sent:
                for handler in read_handlers:
                    if interrupted():
                        return ""
                    read_response = handler(resolved_text, session)
                    if read_response and read_response.text:
                        logger.info(
                            "Read pipeline hit: handler=%s session=%s",
                            handler.__name__,
                            session_id,
                        )
                        # Read-only pipelines already produce user-facing speech text.
                        # Do not run the separate TTS LLM here: it is optimized for short acknowledgements
                        # and can omit/alter the extracted content (e.g., order list summaries).
                        await self._sender.send_tts_response(session_id, read_response.text)
                        return read_response.text

        if session and session.context:
            detail = session.context.get("product_detail")
            if isinstance(detail, dict) and detail.get("options_list"):
                options_list = detail.get("options_list") or {}
                option_keys = list(options_list.keys()) if isinstance(options_list, dict) else []
                logger.info(
                    "LLM context has options_list: session=%s keys=%s",
                    session_id,
                    option_keys,
                )

        response = await self._llm.generate_commands(
            resolved_text,
            intent,
            session
        )
        if interrupted():
            return ""

        if response and response.commands:
            allow_option = is_option_request(resolved_text)
            coerced_commands, changed = coerce_option_clicks(response.commands, session, allow_option)
            if changed:
                logger.info(
                    "Adjusted option commands (allow=%s): session=%s",
                    allow_option,
                    session_id,
                )
            response.commands = coerced_commands

        if response.requires_flow and self._flow:
            flow_type = response.flow_type
            site = session.current_site or "coupang"
            step = await self._flow.start_flow(flow_type, site, session)
            if interrupted():
                return ""
            await self._sender.send_flow_step(session_id, step)
            return ""

        allow_extract = bool(intent and intent.intent == IntentType.SEARCH)
        if not allow_extract and response.commands:
            allow_extract = any(
                (cmd.tool_name or "").startswith("extract")
                for cmd in response.commands
            )
        commands = self._command_pipeline.prepare_commands(
            session_id,
            response.commands,
            session.current_url or "",
            allow_extract=allow_extract,
        )
        self._maybe_set_last_added_product(session_id, session, commands, session.current_url or "")
        if session:
            page_type = get_page_type(session.current_url or "") if session.current_url else None
        else:
            page_type = None
        ack_text = None
        if response and not (response.text or "").strip():
            ack_text = self._fast_ack.get_ack(
                resolved_text,
                page_type,
                intent.intent if intent else None,
                commands,
            )
        if ack_text and not compound_read_sent:
            logger.info("Fast ACK sent: session=%s text='%s...'", session_id, ack_text[:80])
            await self._sender.send_tts_response(session_id, ack_text)
        elif not compound_read_sent and response and (response.text or "").strip():
            logger.info("Fast ACK skipped: response_text_present session=%s", session_id)
        if not commands:
            logger.info(
                "No commands generated for session=%s text='%s'",
                session_id,
                resolved_text[:80]
            )
        tts_text = await self._command_pipeline.dispatch(
            session_id,
            commands,
            response.text,
            session.current_url or "",
            interrupted,
        )
        return tts_text or ""

    def _maybe_set_last_added_product(self, session_id: str, session, commands, current_url: str) -> None:
        if not session or not session.context or not commands or not current_url:
            return
        selector = get_selector(current_url, "add_to_cart")
        if not selector:
            return
        is_add_to_cart = False
        for cmd in commands:
            tool = getattr(cmd, "tool_name", "") or ""
            args = getattr(cmd, "arguments", {}) or {}
            if tool in ("click", "click_element") and args.get("selector") == selector:
                is_add_to_cart = True
                break
            if tool == "click_text" and (args.get("text") or "").strip() == "장바구니 담기":
                is_add_to_cart = True
                break
        if not is_add_to_cart:
            return
        name = self._extract_product_name(session.context)
        if name:
            session.context["last_added_product"] = name
            logger.info("Set last_added_product: session=%s name=%s", session_id, name)

    @staticmethod
    def _extract_product_name(context) -> str:
        if not isinstance(context, dict):
            return ""
        detail = context.get("product_detail")
        if isinstance(detail, dict):
            for key in ("name", "product_name", "title", "productTitle", "product"):
                value = detail.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        last_mentioned = context.get("last_mentioned_product")
        if isinstance(last_mentioned, str):
            return last_mentioned.strip()
        return ""

    async def _wait_for_product_detail(self, session, session_id: str, interrupted) -> bool:
        if not session or not session.context:
            return False
        if has_recent_product_detail(session):
            return True
        deadline = time.time() + 4.5
        while time.time() < deadline:
            if interrupted():
                return False
            await asyncio.sleep(0.5)
            if has_recent_product_detail(session):
                logger.info(
                    "Product detail arrived after wait: session=%s",
                    session_id,
                )
                return True
        logger.info(
            "Product detail not available after wait: session=%s",
            session_id,
        )
        return False
