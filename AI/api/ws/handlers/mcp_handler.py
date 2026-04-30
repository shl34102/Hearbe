# -*- coding: utf-8 -*-
"""
MCP result handler: HTML/OCR summary -> TTS
"""

import asyncio
import json
import logging
import re
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
from urllib.parse import urlparse

from core.interfaces import MCPCommand
from core.event_bus import EventType, publish
from services.llm.sites.site_manager import get_page_type
from services.llm.planner.selection.option_select import CTX_PENDING_OPTION, select_option_from_detail
from services.llm.generators.tts_generator import TTSGenerator, MORE_PROMPT_COUNT
from ..utils.temp_file_manager import TempFileManager

# Summarizer imports (HTML parser + OCR integrator)
try:
    from services.summarizer import (
        parse_product_html,
        detect_site,
        get_ocr_integrator,
    )
    SUMMARIZER_AVAILABLE = True
except ImportError:
    SUMMARIZER_AVAILABLE = False

logger = logging.getLogger(__name__)


class MCPHandler:
    """Handles MCP execution results and summary pipeline."""

    def __init__(
        self,
        sender,
        session_manager,
        action_feedback,
        failure_notifier=None,
        login_guard=None,
        login_feedback=None,
        dom_fallback=None,
        command_queue=None,
    ):
        self._sender = sender
        self._session = session_manager
        self._action_feedback = action_feedback
        self._failure_notifier = failure_notifier
        self._login_guard = login_guard
        self._login_feedback = login_feedback
        self._dom_fallback = dom_fallback
        self._command_queue = command_queue
        self._file_manager = TempFileManager()  # Manages temporary JSON files
        self._ocr_file_manager = TempFileManager()  # Separate tracker for OCR result files
        self._tts = TTSGenerator()

    async def handle_mcp_result(self, session_id: str, data: Dict[str, Any]):
        """
        Handle MCP execution result from client.

        처리 흐름 (스트리밍 방식):
        1. HTML 파싱 → TTS #1 (즉시, 빠른 응답)
        2. OCR 처리 → TTS #2, #3... (청크 단위, 순차 응답)
        """
        success = data.get("success", False)
        result = data.get("result", {})
        error = data.get("error")
        page_data = data.get("page_data") or {}
        tool_name = data.get("tool_name")
        arguments = data.get("arguments") or {}
        request_id = data.get("request_id")
        products = page_data.get("products") if isinstance(page_data, dict) else None
        if not products and isinstance(result, dict):
            products = result.get("products")
        cart_items = None
        cart_summary = None
        order_list = None

        page_url = None
        if isinstance(page_data, dict):
            page_url = page_data.get("url")
        if not page_url and isinstance(result, dict):
            page_url = (
                result.get("current_url")
                or result.get("page_url")
                or result.get("url")
            )

        html_content = None
        detail_images = []
        if isinstance(page_data, dict):
            html_content = page_data.get("html")
            detail_images = page_data.get("detail_images") or []
        if not html_content and isinstance(result, dict):
            html_content = result.get("html")
        if not detail_images and isinstance(result, dict):
            detail_images = result.get("detail_images") or result.get("images") or []

        await publish(
            EventType.MCP_RESULT_RECEIVED,
            data={"success": success, "result": result, "error": error, "page_data": page_data},
            session_id=session_id
        )

        session = self._session.get_session(session_id) if self._session else None
        request_ts = _extract_request_ts(request_id)
        if session and tool_name == "wait_for_new_page":
            nav_ok = bool(result.get("new_page") or result.get("url_changed"))
            self._session.set_context(session_id, "nav_wait_ok", nav_ok)
            if request_ts:
                self._session.set_context(session_id, "nav_wait_ts", request_ts)
        interrupt_ts = None
        if self._session:
            interrupt_ts = self._session.get_context(session_id, "interrupt_ts")
        pre_interrupt = bool(interrupt_ts and request_ts and request_ts <= interrupt_ts)
        is_extract = bool(tool_name and tool_name.startswith("extract"))

        if pre_interrupt and not is_extract:
            logger.info(
                "Skipping MCP result due to interrupt: session=%s tool=%s request_id=%s",
                session_id,
                tool_name,
                request_id
            )
            return

        suppress_outputs = pre_interrupt

        if session and tool_name == "extract_detail":
            nav_wait_ok = self._session.get_context(session_id, "nav_wait_ok")
            nav_wait_ts = self._session.get_context(session_id, "nav_wait_ts")
            page_type = get_page_type(page_url or session.current_url or "")
            if nav_wait_ts and request_ts and request_ts >= nav_wait_ts:
                if not nav_wait_ok and page_type != "product":
                    logger.info(
                        "Skipping extract_detail (no navigation detected): session=%s url=%s",
                        session_id,
                        page_url or session.current_url or ""
                    )
                    return

        if not suppress_outputs and tool_name == "get_dom_snapshot" and self._dom_fallback:
            handled = await self._dom_fallback.handle_dom_snapshot(
                session_id=session_id,
                result=result if isinstance(result, dict) else {},
                current_url=page_url or (session.current_url if session else ""),
            )
            if handled:
                return

        handled = False
        if not suppress_outputs:
            handled = await self._action_feedback.handle_mcp_result(
                session_id=session_id,
                tool_name=tool_name,
                arguments=arguments,
                success=success,
                result=result
            )
            # If ActionFeedback kicked off a cart-verification flow (e.g. add-to-cart verify),
            # suppress the auto cart summary TTS that would otherwise fire on the cart page.
            # This keeps the flow responsive for the next user command (e.g. "결제해").
            if session and self._session:
                try:
                    pending_type = None
                    if self._action_feedback:
                        pending_type = self._action_feedback.get_pending_action_type(session_id)
                    if pending_type in ("add_to_cart_verify", "checkout_verify"):
                        self._session.set_context(
                            session_id,
                            "cart_summary_suppress_until",
                            time.time() + 45,
                        )
                except Exception:
                    pass
            if self._failure_notifier:
                if self._dom_fallback:
                    triggered = await self._dom_fallback.maybe_trigger(
                        session_id=session_id,
                        tool_name=tool_name,
                        arguments=arguments,
                        error=error,
                        current_url=page_url or (session.current_url if session else ""),
                        success=success,
                    )
                    if triggered:
                        return
                await self._failure_notifier.handle_mcp_result(
                    session_id=session_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    success=success,
                    handled=handled,
                    current_url=page_url or (session.current_url if session else "")
                )
        if session and self._session:
            self._session.set_context(session_id, "mcp_result", result)
            if isinstance(result, dict):
                detail = result.get("detail") or result.get("product_detail")
                if detail:
                    if isinstance(detail, dict):
                        detail = dict(detail)
                        if detail_images:
                            detail.setdefault("detail_images", detail_images)
                        extracted_at = time.time()
                        detail["_extracted_at"] = extracted_at
                        self._session.set_context(
                            session_id,
                            "product_detail_received_at",
                            extracted_at,
                        )
                    self._session.set_context(session_id, "product_detail", detail)
                    self._save_product_detail_to_file(detail, session_id)
                    if isinstance(detail, dict) and detail.get("options_list"):
                        keys = list(detail.get("options_list", {}).keys())
                        logger.info(
                            "Product detail options_list stored: session=%s keys=%s",
                            session_id,
                            keys,
                        )
                    if not suppress_outputs:
                        await self._maybe_handle_pending_option(session_id, session)
                        pending = None
                        if self._session:
                            pending = self._session.get_context(session_id, "pending_product_info_read")
                        if pending:
                            pending_text = pending.get("text") if isinstance(pending, dict) else str(pending)
                            pending_ts = pending.get("ts") if isinstance(pending, dict) else None
                            if pending_ts and time.time() - float(pending_ts) > 30:
                                pending_text = ""
                            if pending_text:
                                from services.llm.pipelines.read.product_info import handle_product_info_read
                                read_response = handle_product_info_read(
                                    pending_text,
                                    session,
                                    allow_action=True,
                                )
                                if read_response and read_response.text:
                                    await self._sender.send_tts_response(
                                        session_id,
                                        read_response.text,
                                    )
                                    logger.info(
                                        "Pending product info read delivered: session=%s",
                                        session_id,
                                    )
                            if self._session:
                                self._session.set_context(session_id, "pending_product_info_read", None)
                if detail_images:
                    self._session.set_context(session_id, "detail_images", detail_images)
                cart_items = result.get("cart_items")
                cart_summary = result.get("cart_summary") or {}
                order_list = result.get("order_list")
                if order_list is None:
                    order_list = result.get("orders")
                if cart_items is not None:
                    self._session.set_context(session_id, "cart_items", cart_items)
                    self._session.set_context(session_id, "cart_summary", cart_summary)
                    self._save_cart_to_file(cart_items, cart_summary, session_id)
                if order_list is not None:
                    self._session.set_context(session_id, "order_list", order_list)
                    self._save_order_list_to_file(order_list, session_id)
                    # Keep this compact; it is critical for diagnosing "N번째 주문 상세보기" failures.
                    try:
                        items = []
                        if isinstance(order_list, list):
                            items = [it for it in order_list if isinstance(it, dict)]
                        elif isinstance(order_list, dict):
                            raw = order_list.get("orders") or order_list.get("items") or order_list.get("order_list")
                            if isinstance(raw, list):
                                items = [it for it in raw if isinstance(it, dict)]
                        detail_urls = [(it.get("detail_url") or "").strip() for it in items]
                        present = sum(1 for u in detail_urls if u)
                        sample = [u for u in detail_urls if u][:3]
                        logger.info(
                            "Order list received: session=%s items=%s detail_url_present=%s sample=%s",
                            session_id,
                            len(items),
                            f"{present}/{len(items)}",
                            [s[:120] for s in sample],
                        )
                    except Exception:
                        pass
            previous_url = session.current_url
            if page_url:
                if previous_url and previous_url != page_url:
                    self._session.set_context(session_id, "previous_url", previous_url)
                session.current_url = page_url
                if self._login_feedback and not suppress_outputs:
                    await self._login_feedback.maybe_announce_login_success(
                        session_id,
                        previous_url,
                        page_url
                    )
            if cart_items is not None:
                suppress_cart_tts = False
                if handled and tool_name == "extract_cart":
                    suppress_cart_tts = True
                if session and self._session:
                    until = self._session.get_context(session_id, "tts_suppress_until", 0)
                    if until and time.time() < float(until):
                        suppress_cart_tts = True
                    cart_until = self._session.get_context(session_id, "cart_summary_suppress_until", 0)
                    if cart_until and time.time() < float(cart_until):
                        suppress_cart_tts = True
                if not suppress_outputs and not suppress_cart_tts:
                    tts_text = self._tts.build_cart_summary(cart_items, cart_summary or {})
                    await self._sender.send_tts_response(session_id, tts_text)
                return
            if order_list is not None:
                # If the user requested "N번째 주문 상세보기" before the async order-list extract finished,
                # continue automatically now that extraction has arrived.
                handled_pending = await self._maybe_handle_pending_order_detail_open(session_id, order_list)
                if handled_pending:
                    return
                if not suppress_outputs:
                    prompt_pending = False
                    if self._session:
                        prompt_pending = bool(
                            self._session.get_context(session_id, "order_list_prompt_pending", False)
                        )
                    if not prompt_pending and self._session:
                        self._session.set_context(session_id, "order_list_prompt_pending", True)
                    if not prompt_pending:
                        previous_url = None
                        if self._session:
                            previous_url = self._session.get_context(session_id, "previous_url")
                        prev_type = get_page_type(previous_url) if previous_url else None
                        if previous_url and page_url and previous_url != page_url and prev_type != "orderlist":
                            tts_text = "주문 목록 페이지로 이동이 완료되었습니다. 주문 목록을 읽어드릴까요?"
                        else:
                            tts_text = "주문 목록을 읽어드릴까요?"
                        await self._sender.send_tts_response(session_id, tts_text)
                return

            if products:
                # Debugging aid: selection-by-URL relies on `url` being present in extracted search results.
                # Keep this log compact to avoid noisy TTS-related logs.
                try:
                    non_empty_urls = 0
                    first_keys = []
                    first_url = ""
                    if isinstance(products, list) and products:
                        for p in products[:10]:
                            if isinstance(p, dict) and (p.get("url") or "").strip():
                                non_empty_urls += 1
                        if isinstance(products[0], dict):
                            first_keys = sorted(list(products[0].keys()))[:20]
                            first_url = (products[0].get("url") or "").strip()
                    logger.info(
                        "Search results received: session=%s count=%s url_present=%s first_url=%s first_keys=%s",
                        session_id,
                        len(products) if isinstance(products, list) else "n/a",
                        f"{non_empty_urls}/10",
                        (first_url[:120] if first_url else ""),
                        first_keys,
                    )
                except Exception:
                    pass
                self._session.set_context(session_id, "search_results", products)
                self._session.set_context(session_id, "search_active_results", products)
                self._session.set_context(session_id, "search_active_label", "all")
                signature = self._build_search_signature(products)
                prev_signature = self._session.get_context(session_id, "search_results_signature")
                is_new_signature = signature != prev_signature
                if is_new_signature:
                    self._session.set_context(session_id, "search_read_index", 0)
                    self._session.set_context(session_id, "search_results_signature", signature)

                # Avoid inflating LLM history / double-reading when the same search results
                # are extracted multiple times (e.g., auto-extract + manual extract).
                if is_new_signature:
                    try:
                        payload = json.dumps(products, ensure_ascii=True)
                        self._session.add_to_history(
                            session_id,
                            "system",
                            f"SEARCH_RESULTS:{payload}"
                        )
                    except Exception:
                        logger.warning("Failed to serialize search_results for history")

                    # Save search results to JSON file (new signature only)
                    self._save_search_results_to_file(products, session_id)

                if not suppress_outputs:
                    announced_sig = self._session.get_context(session_id, "search_results_announced_signature")
                    should_announce = announced_sig != signature
                    if should_announce:
                        start_index = self._session.get_context(session_id, "search_read_index", 0)
                        tts_text, next_index, has_more = self._tts.build_search_list(
                            products,
                            start_index=start_index,
                            count=4,
                            include_total=True,
                            more_prompt=MORE_PROMPT_COUNT
                        )
                        self._session.set_context(session_id, "search_read_index", next_index)
                        if next_index > 0:
                            last_item = products[next_index - 1]
                            name = last_item.get("name") or last_item.get("title") or last_item.get("product_name")
                            if name:
                                self._session.set_context(session_id, "last_mentioned_product", name)
                        self._session.set_context(session_id, "search_results_announced_signature", signature)
                        # Used by SearchQueryHandler to avoid re-reading the same results right after auto-announce.
                        self._session.set_context(session_id, "search_last_announce_ts", time.time())
                        await self._sender.send_tts_response(session_id, tts_text)

        if not suppress_outputs and tool_name == "check_login_status" and self._login_guard:
            handled = await self._login_guard.handle_login_check_result(
                session_id,
                result if isinstance(result, dict) else {},
                page_url or (session.current_url if session else "")
            )
            if handled:
                return

        if not suppress_outputs and tool_name == "handle_captcha_modal":
            if isinstance(result, dict) and result.get("captcha_found"):
                await self._sender.send_tts_response(
                    session_id,
                    self._tts.build_captcha_prompt()
                )
                return

        if not suppress_outputs and SUMMARIZER_AVAILABLE and html_content:
            try:
                site = detect_site(page_url or "")
                product_info = parse_product_html(html_content, site=site, url=page_url or "")

                if product_info.is_valid():
                    html_summary = self._tts.build_product_summary(product_info)
                    logger.info(f"HTML 파싱 완료: {product_info.product_name}")

                if html_summary:
                    await self._sender.send_tts_response(session_id, html_summary)

                    if product_info.detail_images:
                        detail_images = product_info.detail_images

            except Exception as e:
                logger.error(f"HTML 파싱 실패: {e}")

        # HTML 파서가 스킵된 경우 (html_content 없음) fallback: 추출된 product_detail로 기본 정보 TTS
        # 옵션 변경 후에는 자동 요약 억제 (suppress_auto_product_summary_until 플래그)
        if not suppress_outputs and not html_content and tool_name == "extract_detail":
            suppress_summary_until = self._session.get_context(session_id, "suppress_auto_product_summary_until", 0) if self._session else 0
            if suppress_summary_until and time.time() < float(suppress_summary_until):
                logger.info("Auto product info TTS suppressed (option change): session=%s", session_id)
            else:
                detail = self._session.get_context(session_id, "product_detail") if self._session else None
                if isinstance(detail, dict) and detail:
                    try:
                        from services.llm.pipelines.read.product_info import _build_summary
                        auto_summary = _build_summary(detail)
                        if auto_summary and "찾지 못했" not in auto_summary:
                            await self._sender.send_tts_response(session_id, auto_summary)
                            logger.info("Auto product info TTS sent (fallback): session=%s", session_id)
                    except Exception as e:
                        logger.error("Auto product info TTS failed: %s", e)

        if not suppress_outputs and SUMMARIZER_AVAILABLE and detail_images:
            # OCR dedup: skip if same images were already processed for this session
            ocr_sig = self._build_ocr_signature(detail_images)
            prev_ocr_sig = None
            if session and self._session:
                prev_ocr_sig = self._session.get_context(session_id, "ocr_image_signature")
            if ocr_sig and ocr_sig == prev_ocr_sig:
                logger.info("OCR skipped (duplicate images): session=%s sig=%s", session_id, ocr_sig[:60])
            else:
                if session and self._session:
                    self._session.set_context(session_id, "ocr_image_signature", ocr_sig)
                asyncio.create_task(
                    self._process_ocr_batch(session_id, detail_images, page_url)
                )

    async def _maybe_handle_pending_option(self, session_id: str, session) -> None:
        if not session or not self._session:
            return
        pending_text = self._session.get_context(session_id, CTX_PENDING_OPTION)
        if not pending_text:
            return
        response = select_option_from_detail(pending_text, session)
        self._session.set_context(session_id, CTX_PENDING_OPTION, None)
        if not response:
            await self._sender.send_tts_response(
                session_id,
                "옵션 정보를 확인하지 못했습니다. 다시 말씀해주세요."
            )
            return
        commands = [cmd for cmd in (response.commands or []) if not cmd.tool_name.startswith("extract")]
        if commands:
            await self._sender.send_tool_calls(session_id, commands)
        if response.text:
            await self._sender.send_tts_response(session_id, response.text)

    async def _maybe_handle_pending_order_detail_open(self, session_id: str, order_list) -> bool:
        """
        Continue an order-detail navigation request ("N번째 주문 상세보기") that arrived before
        `extract_order_list` completed.
        """
        if not self._session:
            return False
        pending = self._session.get_context(session_id, "pending_order_detail_open")
        if not isinstance(pending, dict):
            return False

        ts = pending.get("ts")
        if ts and time.time() - float(ts) > 60:
            self._session.set_context(session_id, "pending_order_detail_open", None)
            return False

        idx = pending.get("index")
        if not isinstance(idx, int) or idx < 0:
            # Without a stable ordinal we can't safely auto-navigate.
            self._session.set_context(session_id, "pending_order_detail_open", None)
            return False

        items: List[Dict[str, Any]] = []
        if isinstance(order_list, dict):
            raw = order_list.get("orders") or order_list.get("items") or order_list.get("order_list")
            if isinstance(raw, list):
                items = [it for it in raw if isinstance(it, dict)]
        elif isinstance(order_list, list):
            items = [it for it in order_list if isinstance(it, dict)]

        # Keep indexing stable: only consider valid order-detail URLs.
        valid_items: List[Dict[str, Any]] = []
        for it in items:
            url = str(it.get("detail_url") or "")
            if not url:
                continue
            try:
                parsed = urlparse(url)
            except Exception:
                continue
            # Be permissive about a trailing slash to avoid dropping valid items.
            if re.search(r"/ssr/desktop/order/\d+/?$", parsed.path or ""):
                valid_items.append(it)

        self._session.set_context(session_id, "pending_order_detail_open", None)

        if idx >= len(valid_items):
            logger.info(
                "Pending order detail open failed: session=%s index=%s items=%s valid_items=%s",
                session_id,
                idx,
                len(items),
                len(valid_items),
            )
            await self._sender.send_tts_response(
                session_id,
                f"{idx + 1}번째 주문을 찾지 못했어요. 다시 '주문 목록 보여줘'라고 말씀해 주세요.",
            )
            return True

        target = valid_items[idx]
        target_url = (target.get("detail_url") or "").strip()
        if not target_url:
            await self._sender.send_tts_response(
                session_id,
                "주문 상세 페이지로 이동할 링크를 찾지 못했어요. 다시 시도해 주세요.",
            )
            return True

        logger.info(
            "Pending order detail open: session=%s index=%s url=%s",
            session_id,
            idx,
            target_url[:160],
        )
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="goto",
                    arguments={"url": target_url},
                    description="go to order detail (pending)",
                ),
                MCPCommand(
                    tool_name="wait",
                    arguments={"ms": 1800},
                    description="wait for order detail page (pending)",
                ),
            ],
        )
        return True

    def _build_search_signature(self, products: List[Dict[str, Any]]) -> str:
        names = []
        for item in products:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("title") or item.get("product_name")
            if name:
                names.append(name)
        return f"{len(products)}|" + "|".join(names[:10])

    async def _process_ocr_batch(
        self,
        session_id: str,
        image_urls: List[str],
        page_url: Optional[str] = None
    ):
        """
        모든 이미지를 한번에 OCR 처리 후 LLM 요약
        """
        try:
            image_urls = _normalize_image_urls(image_urls, page_url)
            if not image_urls:
                logger.warning("OCR skipped: no valid image URLs after normalization")
                return
            ocr_integrator = get_ocr_integrator()
            site = detect_site(page_url or "")

            logger.info(f"OCR 배치 처리 시작: {len(image_urls)}개 이미지")

            await self._sender.send_ocr_progress(session_id, "started", 0, len(image_urls))

            ocr_result = await ocr_integrator.process_single_batch(image_urls, site=site)

            await self._sender.send_ocr_progress(session_id, "ocr_completed", 50, len(image_urls))

            if ocr_result.error:
                logger.error(f"OCR 처리 오류: {ocr_result.error}")
                await self._sender.send_ocr_progress(
                    session_id,
                    "error",
                    0,
                    len(image_urls),
                    error=ocr_result.error
                )
                return

            if ocr_result.summary:
                tts_text = self._tts.build_ocr_summary(ocr_result)
                if tts_text:
                    await self._sender.send_tts_response(session_id, tts_text)

            session = self._session.get_session(session_id) if self._session else None
            if session and self._session:
                ocr_payload = ocr_result.to_dict()
                self._session.set_context(session_id, "ocr_result", ocr_payload)
                detail = self._session.get_context(session_id, "product_detail")
                if isinstance(detail, dict):
                    updated = dict(detail)
                    updated.setdefault("detail_images", image_urls)
                    updated.setdefault("ocr_summary", ocr_payload.get("summary", []))
                    updated.setdefault("ocr_keywords", ocr_payload.get("keywords", {}))
                    updated.setdefault("ocr_product_type", ocr_payload.get("product_type"))
                    self._session.set_context(session_id, "product_detail", updated)

            # Save OCR result to temp JSON for developer inspection
            self._save_ocr_result_to_file(ocr_payload, session_id)

            await self._sender.send_ocr_progress(session_id, "completed", 100, len(image_urls))
            logger.info(f"OCR 배치 처리 완료: {session_id}")

        except Exception as e:
            logger.error(f"OCR 배치 처리 실패: {e}")
            await self._sender.send_ocr_progress(
                session_id,
                "error",
                0,
                len(image_urls),
                error=str(e)
            )

    def _save_search_results_to_file(self, products: List[Dict[str, Any]], session_id: str):
        self._file_manager.save_json(
            data=products,
            session_id=session_id,
            category="search_results",
            filename_prefix="search_results"
        )

    def _save_product_detail_to_file(self, detail: Dict[str, Any], session_id: str):
        self._file_manager.save_json(
            data=detail,
            session_id=session_id,
            category="product_detail",
            filename_prefix="product_detail"
        )

    def _save_cart_to_file(self, items: List[Dict[str, Any]], summary: Dict[str, Any], session_id: str):
        payload = {
            "items": items,
            "summary": summary,
        }
        self._file_manager.save_json(
            data=payload,
            session_id=session_id,
            category="cart",
            filename_prefix="cart"
        )

    def _save_ocr_result_to_file(self, ocr_payload: Dict[str, Any], session_id: str):
        self._ocr_file_manager.save_json(
            data=ocr_payload,
            session_id=session_id,
            category="ocr_results",
            filename_prefix="ocr_result"
        )

    def _build_ocr_signature(self, image_urls: List[str]) -> str:
        """Build a signature from sorted image URLs for dedup."""
        sorted_urls = sorted(set(url.strip() for url in image_urls if isinstance(url, str) and url.strip()))
        return f"{len(sorted_urls)}|" + "|".join(sorted_urls[:20])

    def _save_order_list_to_file(self, orders: List[Dict[str, Any]], session_id: str):
        payload = {
            "orders": orders or [],
            "count": len(orders or []),
        }
        self._file_manager.save_json(
            data=payload,
            session_id=session_id,
            category="order_list",
            filename_prefix="order_list"
        )

    def cleanup_session(self, session_id: str):
        self._file_manager.cleanup_session(session_id)
        self._ocr_file_manager.cleanup_session(session_id)


def _normalize_image_urls(urls: List[str], base_url: Optional[str] = None) -> List[str]:
    if not urls:
        return []
    seen = set()
    normalized: List[str] = []
    for raw in urls:
        if not isinstance(raw, str):
            continue
        url = raw.strip()
        if not url:
            continue
        if url.startswith(("data:", "blob:", "javascript:")):
            continue
        if url.startswith("//"):
            url = f"https:{url}"
        elif url.startswith("/") and base_url:
            url = urljoin(base_url, url)
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        normalized.append(url)
    return normalized


def _extract_request_ts(request_id: Optional[str]) -> Optional[float]:
    if not request_id:
        return None
    parts = request_id.split("_")
    if len(parts) < 3:
        return None
    try:
        return float(parts[-2])
    except ValueError:
        return None
