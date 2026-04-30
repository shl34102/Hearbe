from __future__ import annotations

import re
import time
from typing import Optional, Dict, Any, List, Tuple

from core.interfaces import LLMResponse, MCPCommand, SessionState
from core.korean_numbers import extract_ordinal_index, replace_korean_number_units
from services.llm.rules.option_utils import (
    build_option_list_text,
    is_option_change_request,
)
from .selection_extract import build_product_extract_command
from ...sites.site_manager import get_page_type


CTX_PENDING_OPTION = "pending_option_request"


def select_option_from_detail(
    user_text: str,
    session: Optional[SessionState]
) -> Optional[LLMResponse]:
    if not session:
        return None

    current_url = session.current_url or ""
    if current_url and get_page_type(current_url) != "product":
        return None

    target = user_text.strip()
    if not target:
        return None

    if not is_option_change_request(target):
        return None

    detail = session.context.get("product_detail") if isinstance(session.context, dict) else None
    if not isinstance(detail, dict) or not detail:
        return _build_pending_option_response(target, session)

    options_list = detail.get("options_list")
    if not isinstance(options_list, dict) or not options_list:
        return _build_pending_option_response(target, session)

    candidates = _flatten_options(options_list)
    if not candidates:
        return None

    ordinal_index = extract_ordinal_index(target.lower())
    if ordinal_index is not None:
        keys = {key for key, _, _ in candidates}
        if len(keys) != 1:
            ordinal_index = None
    if ordinal_index is not None:
        ordinal_match = _select_by_ordinal(candidates, ordinal_index)
        if ordinal_match:
            key, name, _ = ordinal_match
            return _build_option_click_response(name, key, detail, session)

    best = _select_by_text_match(target, candidates)
    if not best:
        return _build_option_list_response(options_list)

    key, name, _ = best
    return _build_option_click_response(name, key, detail, session)


def is_option_request(text: str) -> bool:
    return is_option_change_request(text)


def _flatten_options(options_list: Dict[str, Any]) -> List[Tuple[str, str, bool]]:
    flattened: List[Tuple[str, str, bool]] = []
    for key, items in options_list.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            selected = bool(item.get("selected"))
            flattened.append((key, str(name), selected))
    return flattened


def _select_by_ordinal(
    candidates: List[Tuple[str, str, bool]],
    ordinal_index: int
) -> Optional[Tuple[str, str, bool]]:
    if ordinal_index < 0 or ordinal_index >= len(candidates):
        return None
    return candidates[ordinal_index]


def _select_by_text_match(
    user_text: str,
    candidates: List[Tuple[str, str, bool]]
) -> Optional[Tuple[str, str, bool]]:
    query = _normalize(user_text)
    if not query:
        return None

    tokens = _extract_tokens(user_text)
    best_score = 0
    best_candidate: Optional[Tuple[str, str, bool]] = None

    for key, name, selected in candidates:
        candidate_norm = _normalize(name)
        if not candidate_norm:
            continue
        score = 0
        matched = False
        if candidate_norm in query or query in candidate_norm:
            score += 100
            matched = True
        for token in tokens:
            if token and token in name:
                score += 10
                matched = True
        if matched:
            score += min(len(candidate_norm), 30)
        if score > best_score:
            best_score = score
            best_candidate = (key, name, selected)

    return best_candidate if best_score > 0 else None


def _normalize(text: str) -> str:
    cleaned = replace_korean_number_units(text).lower().replace("×", "x")
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", cleaned)


def _extract_tokens(text: str) -> List[str]:
    converted = replace_korean_number_units(text)
    return re.findall(r"\d+(?:[\.,]\d+)?(?:[a-zA-Z가-힣%]+)?", converted)


def _build_option_click_response(
    option_name: str,
    key: str,
    detail: Dict[str, Any],
    session: SessionState
) -> Optional[LLMResponse]:
    if not option_name:
        return None

    current_options = detail.get("options")
    if isinstance(current_options, dict):
        current_value = current_options.get(key)
        if current_value and option_name in str(current_value):
            _clear_pending_option(session)
            return LLMResponse(
                text=f"이미 선택된 옵션입니다: {option_name}",
                commands=[],
                requires_flow=False,
                flow_type=None,
            )

    selector = _build_option_selector(option_name)
    commands = [
        MCPCommand(
            tool_name="click",
            arguments={"selector": selector},
            description=f"select option '{option_name}' within option table"
        ),
        MCPCommand(
            tool_name="wait",
            arguments={"ms": 800},
            description="wait for option update"
        ),
    ]
    extract_command = build_product_extract_command(session)
    if extract_command:
        commands.append(extract_command)

    _clear_pending_option(session)
    # 옵션 변경 후 extract_detail 결과로 인한 자동 상품 요약 TTS 억제
    if isinstance(session.context, dict):
        session.context["suppress_auto_product_summary_until"] = time.time() + 10
    return LLMResponse(
        text=f"옵션을 변경합니다: {option_name}",
        commands=commands,
        requires_flow=False,
        flow_type=None,
    )


def _build_option_list_response(options_list: Dict[str, Any]) -> Optional[LLMResponse]:
    text = build_option_list_text(options_list)
    if not text:
        return None
    return LLMResponse(
        text=text,
        commands=[],
        requires_flow=False,
        flow_type=None,
    )


def _build_pending_option_response(
    target: str,
    session: SessionState,
) -> Optional[LLMResponse]:
    if session and isinstance(session.context, dict):
        session.context[CTX_PENDING_OPTION] = target

    extract_cmd = build_product_extract_command(session)
    if not extract_cmd:
        return LLMResponse(
            text="옵션 정보를 확인하지 못했습니다. 다시 말씀해주세요.",
            commands=[],
            requires_flow=False,
            flow_type=None,
        )

    return LLMResponse(
        text="옵션 정보를 불러오는 중입니다.",
        commands=[extract_cmd],
        requires_flow=False,
        flow_type=None,
    )


def _clear_pending_option(session: SessionState) -> None:
    if not session or not isinstance(session.context, dict):
        return
    session.context.pop(CTX_PENDING_OPTION, None)


def _build_option_selector(option_name: str) -> str:
    safe_text = option_name.replace('"', '\\"')
    return (
        '.option-table-v2 '
        f'.option-table-list__option:has(.option-table-list__option-name:has-text("{safe_text}"))'
        f', .custom-scrollbar .select-item:has-text("{safe_text}")'
    )


def coerce_option_clicks(
    commands: List[MCPCommand],
    session: Optional[SessionState],
    allow: bool,
) -> tuple[List[MCPCommand], bool]:
    if not session or not commands:
        return commands, False

    current_url = session.current_url or ""
    if current_url and get_page_type(current_url) != "product":
        return commands, False

    context = session.context or {}
    detail = context.get("product_detail")
    if not isinstance(detail, dict) or not detail:
        return commands, False

    options_list = detail.get("options_list")
    if not isinstance(options_list, dict) or not options_list:
        return commands, False

    candidates = _flatten_options(options_list)
    if not candidates:
        return commands, False

    names = []
    seen = set()
    for _, name, _ in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
        if name in seen:
            continue
        seen.add(name)
        names.append(name)

    def match_option(text: str) -> Optional[str]:
        if not text:
            return None
        target = text.strip()
        for name in names:
            if name in target or target in name:
                return name
        return None

    updated: List[MCPCommand] = []
    changed = False
    dropped_last_option_click = False
    for cmd in commands:
        if cmd.tool_name == "click_text":
            match = match_option((cmd.arguments or {}).get("text", ""))
            if match:
                if allow:
                    selector = _build_option_selector(match)
                    updated.append(
                        MCPCommand(
                            tool_name="click",
                            arguments={"selector": selector},
                            description=f"select option '{match}' within option table",
                        )
                    )
                    changed = True
                else:
                    changed = True
                    dropped_last_option_click = True
                continue
        if cmd.tool_name == "click" and not allow:
            selector = (cmd.arguments or {}).get("selector", "")
            if selector and (
                ".option-table" in selector
                or ".option-picker-select" in selector
                or ".option-table-list__option" in selector
                or ".select-item" in selector
            ):
                changed = True
                dropped_last_option_click = True
                continue
        if cmd.tool_name == "wait" and dropped_last_option_click:
            desc = (cmd.description or "").lower()
            if "option" in desc or "옵션" in desc:
                changed = True
                dropped_last_option_click = False
                continue
            dropped_last_option_click = False
        else:
            dropped_last_option_click = False
        updated.append(cmd)

    return updated, changed
