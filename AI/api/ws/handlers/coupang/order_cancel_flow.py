# -*- coding: utf-8 -*-
"""
Coupang order-cancel step-by-step flow.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from core.interfaces import MCPCommand
from core.korean_numbers import extract_ordinal_index
from services.llm.sites.site_manager import get_page_type, get_selector

logger = logging.getLogger(__name__)


CTX_FLOW_ACTIVE = "coupang_cancel_flow_active"
CTX_FLOW_STEP = "coupang_cancel_flow_step"
CTX_FLOW_RETRY = "coupang_cancel_flow_retry"
CTX_FLOW_EXPECT = "coupang_cancel_flow_expect"
CTX_FLOW_ADVANCE = "coupang_cancel_flow_advance"
CTX_FLOW_REASON = "coupang_cancel_flow_reason"

STEP_ENTRY = "entry"
STEP_REASON = "reason"
STEP_REFUND_FETCH = "refund_fetch"
STEP_REFUND_ACTION = "refund_action"
STEP_CONFIRM_WAIT = "confirm_wait"
STEP_CONFIRM_ACTION = "confirm_action"
STEP_COMPLETE_FETCH = "complete_fetch"
STEP_COMPLETE_ACTION = "complete_action"

MAX_RETRIES = 2

REASON_OPTIONS: List[Tuple[str, Tuple[str, ...]]] = [
    ("배송지를 잘못 입력함", ("배송지", "주소", "잘못")),
    ("상품이 마음에 들지 않음 (단순변심)", ("마음", "단순", "변심")),
    ("다른 상품 추가 후 재주문 예정", ("재주문", "다른 상품", "추가 주문")),
    ("상품의 옵션 선택을 잘못함", ("옵션", "선택", "잘못")),
    ("다른 사이트의 가격이 더 저렴함", ("가격", "저렴", "다른 사이트")),
    ("기타", ("기타", "그냥")),
]


class CoupangOrderCancelFlowManager:
    def __init__(self, sender, session_manager):
        self._sender = sender
        self._session = session_manager

    async def handle_page_update(self, session_id: str, url: str) -> bool:
        if not self._sender or not self._session:
            return False
        if not self._session.get_context(session_id, CTX_FLOW_ACTIVE):
            return False
        if not _is_coupang_order_cancel_page(url) and not _is_coupang_order_detail(url):
            self._clear_flow(session_id)
            return False
        return True

    async def handle_user_text(self, session_id: str, text: str) -> bool:
        if not self._sender or not self._session:
            return False
        session = self._session.get_session(session_id)
        if not session:
            return False
        current_url = session.current_url or ""

        active = bool(self._session.get_context(session_id, CTX_FLOW_ACTIVE))
        if not active:
            if not _is_cancel_intent(text):
                return False
            if not (_is_coupang_order_detail(current_url) or _is_coupang_order_cancel_page(current_url)):
                return False
            self._session.set_context(session_id, CTX_FLOW_ACTIVE, True)
            if _is_coupang_order_cancel_page(current_url):
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REASON)
                await self._prompt_reason(session_id)
            else:
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_ENTRY)
                await self._start_entry_step(session_id, current_url)
            return True

        step = self._session.get_context(session_id, CTX_FLOW_STEP) or STEP_ENTRY
        normalized = _normalize(text)
        compact = normalized.replace(" ", "")

        if step == STEP_REASON:
            reason = _resolve_reason(text)
            if not reason:
                await self._sender.send_tts_response(session_id, "취소 사유를 번호로 말씀해 주세요.")
                return True
            self._session.set_context(session_id, CTX_FLOW_REASON, reason)
            await self._start_refund_step(session_id, current_url, reason)
            return True

        if step == STEP_REFUND_ACTION:
            if _is_prev_intent(compact):
                await self._click_prev(session_id, current_url)
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REASON)
                await self._prompt_reason(session_id)
                return True
            if _is_submit_intent(compact):
                await self._start_confirm_step(session_id, current_url)
                return True
            await self._sender.send_tts_response(
                session_id,
                "이전 단계로 갈까요, 아니면 신청하기로 진행할까요?",
            )
            return True

        if step == STEP_CONFIRM_ACTION:
            if "장바구니" in normalized:
                await self._click_back_to_cart(session_id, current_url)
                self._clear_flow(session_id)
                return True
            if _is_cancel_modal_intent(compact):
                await self._click_modal_cancel(session_id, current_url)
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REFUND_ACTION)
                await self._sender.send_tts_response(session_id, "취소를 눌렀습니다. 계속 진행할까요?")
                return True
            if _is_confirm_intent(compact):
                await self._start_complete_step(session_id, current_url)
                return True
            await self._sender.send_tts_response(
                session_id,
                "취소 확인, 취소, 장바구니 다시 담기 중에서 말씀해 주세요.",
            )
            return True

        if step == STEP_COMPLETE_ACTION:
            if "신청내역" in normalized:
                await self._click_completion_check(session_id, current_url)
                self._clear_flow(session_id)
                return True
            if "쇼핑" in normalized or "계속" in normalized:
                await self._click_completion_continue(session_id, current_url)
                self._clear_flow(session_id)
                return True
            await self._sender.send_tts_response(
                session_id,
                "신청내역 확인하기 또는 쇼핑 계속하기 중에서 말씀해 주세요.",
            )
            return True

        return True

    async def handle_mcp_result(self, session_id: str, data: dict) -> bool:
        if not self._session or not self._sender:
            return False
        if not self._session.get_context(session_id, CTX_FLOW_ACTIVE):
            return False
        tool_name = data.get("tool_name")
        if not tool_name:
            return False
        arguments = data.get("arguments") or {}
        fp = _fingerprint(tool_name, arguments)
        expected = self._session.get_context(session_id, CTX_FLOW_EXPECT) or []
        if fp not in expected:
            return False

        success = bool(data.get("success", False))
        session = self._session.get_session(session_id)
        current_url = session.current_url if session else ""

        if not success:
            await self._retry_step(session_id, current_url, reason="tool_failed")
            return True

        advance = self._session.get_context(session_id, CTX_FLOW_ADVANCE)
        if advance and fp == advance:
            step = self._session.get_context(session_id, CTX_FLOW_STEP)
            if step == STEP_ENTRY:
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REASON)
                await self._prompt_reason(session_id)
            elif step == STEP_REFUND_FETCH:
                refund_text = _build_refund_tts(data)
                await self._sender.send_tts_response(session_id, refund_text)
                await self._sender.send_tts_response(
                    session_id,
                    "이전 단계로 갈까요, 아니면 신청하기로 진행할까요?",
                )
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REFUND_ACTION)
            elif step == STEP_CONFIRM_WAIT:
                await self._sender.send_tts_response(
                    session_id,
                    "취소 신청하시겠습니까? 장바구니 다시 담기, 취소, 확인 중에서 말씀해 주세요.",
                )
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_CONFIRM_ACTION)
            elif step == STEP_COMPLETE_FETCH:
                complete_text = _build_completion_tts(data)
                await self._sender.send_tts_response(session_id, complete_text)
                await self._sender.send_tts_response(
                    session_id,
                    "신청내역 확인하기 또는 쇼핑 계속하기 중에서 말씀해 주세요.",
                )
                self._session.set_context(session_id, CTX_FLOW_STEP, STEP_COMPLETE_ACTION)
            return True
        return False

    def cleanup_session(self, session_id: str) -> None:
        self._clear_flow(session_id)

    async def _start_entry_step(self, session_id: str, current_url: str) -> None:
        await self._sender.send_tts_response(
            session_id,
            "주문 취소를 시작합니다. 취소 화면으로 이동할게요.",
        )
        entry_selector = get_selector(current_url, "cancel_entry") if current_url else None
        wait_selector = get_selector(current_url, "cancel_reason_heading") if current_url else None
        if not wait_selector:
            wait_selector = "text=취소 사유를 선택해주세요"

        commands: List[MCPCommand] = []
        if entry_selector:
            commands.append(
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": entry_selector},
                    description="주문 취소 진입 버튼 클릭",
                )
            )
        else:
            commands.append(
                MCPCommand(
                    tool_name="click_text",
                    arguments={"text": "주문 · 배송 취소"},
                    description="주문 · 배송 취소 텍스트 클릭",
                )
            )
        commands.append(
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": wait_selector, "state": "visible", "timeout": 12000},
                description="취소 사유 화면 로드 대기",
            )
        )

        self._set_expectations(session_id, commands, advance_index=len(commands) - 1)
        await self._sender.send_tool_calls(session_id, commands)
        self._session.set_context(session_id, CTX_FLOW_STEP, STEP_ENTRY)

    async def _prompt_reason(self, session_id: str) -> None:
        lines = [
            "취소 사유를 선택해주세요.",
            "1번 배송지를 잘못 입력함.",
            "2번 상품이 마음에 들지 않음.",
            "3번 다른 상품 추가 후 재주문 예정.",
            "4번 상품의 옵션 선택을 잘못함.",
            "5번 다른 사이트의 가격이 더 저렴함.",
            "6번 기타.",
        ]
        await self._sender.send_tts_response(session_id, " ".join(lines))
        self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REASON)

    async def _start_refund_step(self, session_id: str, current_url: str, reason: str) -> None:
        await self._sender.send_tts_response(session_id, f"취소 사유는 {reason}로 선택하겠습니다.")
        reason_selector = _reason_to_selector(reason)
        next_selector = (
            get_selector(current_url, "cancel_next")
            or "button:has-text('다음 단계'):not([disabled]):not([aria-disabled='true'])"
        )
        refund_selector = get_selector(current_url, "refund_section") or "text=환불안내"

        commands: List[MCPCommand] = [
            MCPCommand(
                tool_name="click_text",
                arguments={"text": reason_selector},
                description="취소 사유 선택",
            ),
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": next_selector, "state": "visible", "timeout": 8000},
                description="다음 단계 활성 대기",
            ),
            MCPCommand(
                tool_name="click",
                arguments={"selector": next_selector},
                description="취소 플로우 다음 단계 클릭",
            ),
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": refund_selector, "state": "visible", "timeout": 12000},
                description="환불 안내 영역 대기",
            ),
            MCPCommand(
                tool_name="get_dom_snapshot",
                arguments={"include_frames": False, "max_chars": 400000},
                description="환불 안내 정보 추출",
            ),
        ]
        self._set_expectations(session_id, commands, advance_index=len(commands) - 1)
        await self._sender.send_tool_calls(session_id, commands)
        self._session.set_context(session_id, CTX_FLOW_STEP, STEP_REFUND_FETCH)

    async def _start_confirm_step(self, session_id: str, current_url: str) -> None:
        submit_selector = (
            get_selector(current_url, "cancel_submit")
            or "button:has-text('신청하기'):not([disabled]):not([aria-disabled='true'])"
        )
        modal_selector = get_selector(current_url, "cancel_modal") or "text=취소 신청하시겠습니까?"
        commands: List[MCPCommand] = [
            MCPCommand(
                tool_name="click",
                arguments={"selector": submit_selector},
                description="취소 신청하기 클릭",
            ),
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": modal_selector, "state": "visible", "timeout": 8000},
                description="취소 확인 모달 대기",
            ),
        ]
        self._set_expectations(session_id, commands, advance_index=len(commands) - 1)
        await self._sender.send_tool_calls(session_id, commands)
        self._session.set_context(session_id, CTX_FLOW_STEP, STEP_CONFIRM_WAIT)

    async def _start_complete_step(self, session_id: str, current_url: str) -> None:
        confirm_selector = get_selector(current_url, "cancel_modal_confirm") or "button:has-text('확인')"
        complete_selector = get_selector(current_url, "cancel_complete_title") or "text=취소 신청이 완료되었습니다"
        commands: List[MCPCommand] = [
            MCPCommand(
                tool_name="click",
                arguments={"selector": confirm_selector},
                description="취소 확인 클릭",
            ),
            MCPCommand(
                tool_name="wait_for_selector",
                arguments={"selector": complete_selector, "state": "visible", "timeout": 12000},
                description="취소 완료 화면 대기",
            ),
            MCPCommand(
                tool_name="get_dom_snapshot",
                arguments={"include_frames": False, "max_chars": 400000},
                description="취소 완료 정보 추출",
            ),
        ]
        self._set_expectations(session_id, commands, advance_index=len(commands) - 1)
        await self._sender.send_tool_calls(session_id, commands)
        self._session.set_context(session_id, CTX_FLOW_STEP, STEP_COMPLETE_FETCH)

    async def _click_prev(self, session_id: str, current_url: str) -> None:
        prev_selector = get_selector(current_url, "cancel_prev") or "button:has-text('이전 단계')"
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": prev_selector},
                    description="이전 단계 클릭",
                )
            ],
        )

    async def _click_back_to_cart(self, session_id: str, current_url: str) -> None:
        back_selector = get_selector(current_url, "cancel_back_to_cart") or "button:has-text('장바구니 다시 담기')"
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": back_selector},
                    description="장바구니 다시 담기 클릭",
                )
            ],
        )

    async def _click_modal_cancel(self, session_id: str, current_url: str) -> None:
        cancel_selector = get_selector(current_url, "cancel_modal_cancel") or "button:has-text('취소')"
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": cancel_selector},
                    description="취소 모달 취소 클릭",
                )
            ],
        )

    async def _click_completion_check(self, session_id: str, current_url: str) -> None:
        selector = get_selector(current_url, "cancel_complete_check") or "button:has-text('신청내역 확인하기')"
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": selector},
                    description="신청내역 확인하기 클릭",
                )
            ],
        )

    async def _click_completion_continue(self, session_id: str, current_url: str) -> None:
        selector = get_selector(current_url, "cancel_complete_continue") or "button:has-text('쇼핑 계속하기')"
        await self._sender.send_tool_calls(
            session_id,
            [
                MCPCommand(
                    tool_name="click",
                    arguments={"selector": selector},
                    description="쇼핑 계속하기 클릭",
                )
            ],
        )

    async def _retry_step(self, session_id: str, current_url: str, reason: str) -> None:
        retries = self._session.get_context(session_id, CTX_FLOW_RETRY, 0)
        try:
            retries = int(retries)
        except Exception:
            retries = 0
        retries += 1
        self._session.set_context(session_id, CTX_FLOW_RETRY, retries)
        if retries > MAX_RETRIES:
            await self._sender.send_tts_response(
                session_id,
                "주문 취소를 계속 진행하지 못했습니다. 다시 말씀해 주세요.",
            )
            self._clear_flow(session_id)
            return
        await self._sender.send_tts_response(session_id, "오류가 있어 다시 시도하겠습니다.")
        step = self._session.get_context(session_id, CTX_FLOW_STEP)
        if step == STEP_ENTRY:
            await self._start_entry_step(session_id, current_url)
        elif step == STEP_REFUND_FETCH:
            reason = self._session.get_context(session_id, CTX_FLOW_REASON) or REASON_OPTIONS[0][0]
            await self._start_refund_step(session_id, current_url, reason)
        elif step == STEP_CONFIRM_WAIT:
            await self._start_confirm_step(session_id, current_url)
        elif step == STEP_COMPLETE_FETCH:
            await self._start_complete_step(session_id, current_url)
        logger.info("Cancel flow retry: session=%s reason=%s retry=%s", session_id, reason, retries)

    def _set_expectations(self, session_id: str, commands: List[MCPCommand], advance_index: int) -> None:
        fingerprints = [_fingerprint(c.tool_name, c.arguments) for c in commands]
        advance = fingerprints[advance_index] if 0 <= advance_index < len(fingerprints) else None
        self._session.set_context(session_id, CTX_FLOW_EXPECT, fingerprints)
        self._session.set_context(session_id, CTX_FLOW_ADVANCE, advance)

    def _clear_flow(self, session_id: str) -> None:
        if not self._session:
            return
        self._session.set_context(session_id, CTX_FLOW_ACTIVE, None)
        self._session.set_context(session_id, CTX_FLOW_STEP, None)
        self._session.set_context(session_id, CTX_FLOW_RETRY, None)
        self._session.set_context(session_id, CTX_FLOW_EXPECT, None)
        self._session.set_context(session_id, CTX_FLOW_ADVANCE, None)
        self._session.set_context(session_id, CTX_FLOW_REASON, None)


def _is_cancel_intent(text: str) -> bool:
    if not text:
        return False
    compact = _normalize(text).replace(" ", "")
    return any(
        token in compact
        for token in ("주문취소", "배송취소", "취소할게", "취소해줘", "취소해", "취소")
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _is_prev_intent(text: str) -> bool:
    return any(k in text for k in ("이전", "뒤로", "돌아가"))


def _is_submit_intent(text: str) -> bool:
    return any(k in text for k in ("신청", "진행", "다음", "계속"))


def _is_confirm_intent(text: str) -> bool:
    return any(k in text for k in ("확인", "진행", "맞아", "응", "네", "예"))


def _is_cancel_modal_intent(text: str) -> bool:
    return any(k in text for k in ("취소", "아니", "그만"))


def _resolve_reason(text: str) -> Optional[str]:
    normalized = _normalize(text)
    ordinal = extract_ordinal_index(normalized)
    if ordinal is not None and 0 <= ordinal < len(REASON_OPTIONS):
        return REASON_OPTIONS[ordinal][0]
    for label, keywords in REASON_OPTIONS:
        for key in keywords:
            if key and key in normalized:
                return label
    return None


def _reason_to_selector(label: str) -> str:
    return label


def _is_coupang_order_detail(url: str) -> bool:
    if not url:
        return False
    if get_page_type(url) == "orderdetail":
        return True
    return bool(re.search(r"mc\.coupang\.com/ssr/desktop/order/\d+", url))


def _is_coupang_order_cancel_page(url: str) -> bool:
    if not url:
        return False
    if get_page_type(url) == "ordercancel":
        return True
    return bool(re.search(r"mc\.coupang\.com/ssr/desktop/cancel-flow", url))


def _fingerprint(tool_name: str, arguments: dict) -> str:
    try:
        payload = json.dumps(arguments or {}, sort_keys=True, ensure_ascii=True)
    except Exception:
        payload = str(arguments)
    return f"{tool_name}:{payload}"


def _strip_tags(dom: str) -> str:
    text = re.sub(r"<[^>]+>", " ", dom or "")
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_label_amount(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*([0-9,]+\s*원)", text)
    return match.group(1).strip() if match else ""


def _extract_refund_method(text: str) -> str:
    match = re.search(r"환불 수단\s*([가-힣A-Za-z0-9\s]+?)\s*([0-9,]+\s*원)", text)
    if match:
        return f"{match.group(1).strip()} {match.group(2).strip()}".strip()
    return ""


def _build_refund_tts(data: dict) -> str:
    dom = _resolve_dom(data)
    if not dom:
        return "환불 안내 정보를 확인하지 못했습니다."
    text = _strip_tags(dom)
    product = _extract_label_amount(text, "상품금액")
    delivery = _extract_label_amount(text, "배송비")
    return_fee = _extract_label_amount(text, "반품비")
    expected = _extract_label_amount(text, "환불 예상금액")
    method = _extract_refund_method(text)
    parts = ["환불 안내입니다."]
    if product:
        parts.append(f"상품금액 {product}.")
    if delivery:
        parts.append(f"배송비 {delivery}.")
    if return_fee:
        parts.append(f"반품비 {return_fee}.")
    if expected:
        parts.append(f"환불 예상금액 {expected}.")
    if method:
        parts.append(f"환불 수단 {method}입니다.")
    if len(parts) == 1:
        return "환불 안내 정보를 확인하지 못했습니다."
    return " ".join(parts)


def _build_completion_tts(data: dict) -> str:
    dom = _resolve_dom(data)
    if not dom:
        return "취소 신청이 완료되었습니다."
    text = _strip_tags(dom)
    refund_date = _extract_label_value(text, "환불 예정일")
    refund_method = _extract_label_value(text, "환불 수단")
    parts = ["취소 신청이 완료되었습니다."]
    if refund_date:
        parts.append(f"환불 예정일은 {refund_date}입니다.")
    if refund_method:
        parts.append(f"환불 수단은 {refund_method}입니다.")
    return " ".join(parts)


def _extract_label_value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*([가-힣A-Za-z0-9\s]+)", text)
    if not match:
        return ""
    value = match.group(1).strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _resolve_dom(data: dict) -> str:
    result = data.get("result") or {}
    if isinstance(result, dict):
        dom = result.get("dom")
        if dom:
            return dom
    return ""


__all__ = ["CoupangOrderCancelFlowManager"]
