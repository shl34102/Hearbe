from __future__ import annotations

from typing import Optional, Dict, Any

from core.interfaces import LLMResponse, SessionState
from services.llm.sites.site_manager import get_page_type
from services.llm.planner.selection.option_select import select_option_from_detail
from services.llm.planner.selection.selection_extract import build_product_extract_command
from services.llm.rules.option_utils import (
    build_option_list_text,
    find_option_match,
    find_selected_prices,
    is_option_change_request,
    is_option_list_query,
    is_option_price_query,
    is_option_related,
    list_option_prices,
)


def handle_product_option_rule(
    user_text: str,
    session: Optional[SessionState],
) -> Optional[LLMResponse]:
    if not session:
        return None

    current_url = session.current_url or ""
    if not current_url or get_page_type(current_url) != "product":
        return None

    text = user_text.strip()
    if not text:
        return None

    if not is_option_related(text):
        return None

    detail = session.context.get("product_detail") if isinstance(session.context, dict) else None
    options_list = detail.get("options_list") if isinstance(detail, dict) else None

    if is_option_price_query(text):
        return _build_option_price_response(text, options_list, session)

    if is_option_list_query(text):
        return _build_option_list_response(options_list, session)

    if is_option_change_request(text):
        return select_option_from_detail(text, session)

    return None


def _build_option_list_response(
    options_list: Optional[Dict[str, Any]],
    session: SessionState,
) -> Optional[LLMResponse]:
    if not isinstance(options_list, dict) or not options_list:
        return _build_option_extract_response(session, "옵션 정보를 확인하겠습니다.")
    text = build_option_list_text(options_list)
    if not text:
        return None
    return LLMResponse(text=text, commands=[], requires_flow=False, flow_type=None)


def _build_option_price_response(
    text: str,
    options_list: Optional[Dict[str, Any]],
    session: SessionState,
) -> Optional[LLMResponse]:
    if not isinstance(options_list, dict) or not options_list:
        return _build_option_extract_response(session, "옵션 가격을 확인하겠습니다.")

    matched = find_option_match(text, options_list)
    if matched:
        name, price = matched
        if price:
            return LLMResponse(
                text=f"{name} 옵션 가격은 {price}입니다.",
                commands=[],
                requires_flow=False,
                flow_type=None,
            )

    selected_prices = find_selected_prices(options_list)
    if selected_prices:
        if len(selected_prices) == 1:
            name, price = selected_prices[0]
            return LLMResponse(
                text=f"현재 선택된 옵션 가격은 {price}입니다.",
                commands=[],
                requires_flow=False,
                flow_type=None,
            )
        joined = ", ".join(f"{name} {price}" for name, price in selected_prices)
        return LLMResponse(
            text=f"현재 선택된 옵션 가격은 {joined}입니다.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    prices = list_option_prices(options_list)
    if prices:
        return LLMResponse(
            text="옵션별 가격은 " + " / ".join(prices) + " 입니다.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    return LLMResponse(
        text="옵션 가격 정보를 찾지 못했습니다.",
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


def _build_option_extract_response(
    session: SessionState,
    message: str,
) -> Optional[LLMResponse]:
    extract_cmd = build_product_extract_command(session)
    if not extract_cmd:
        return LLMResponse(
            text="옵션 정보를 확인하지 못했습니다. 다시 말씀해주세요.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )
    return LLMResponse(
        text=message,
        commands=[extract_cmd],
        requires_flow=False,
        flow_type=None,
    )
