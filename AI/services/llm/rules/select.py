"""
검색 결과 선택 규칙

검색 결과 페이지에서 "선택/열어" 등의 요청은 재검색 없이 클릭으로 처리합니다.
"""

import re
from typing import Optional
from . import BaseRule, RuleResult
from ..context.context_rules import (
    GeneratedCommand,
    build_click_text_command,
    build_click_command,
    build_wait_command,
)
from ..sites.site_manager import get_page_type, get_current_site
from ..planner.selection.site_extractors import build_product_extract_command_for_site
from core.korean_numbers import extract_ordinal_index


# Keep triggers permissive to match natural spoken phrases (e.g. "2번째 상품 들어줘").
SELECTION_TRIGGERS = [
    "선택",
    "골라",
    "고르",
    "열어",
    "열어줘",
    "열어봐",
    "들어",
    "들어가",
    "들어줘",
    "눌러",
    "클릭",
]
FILLER_WORDS = ["그거", "이거", "저거", "해줘", "해주세요", "해", "좀", "줘", "봐", "봐줘", "상품", "결과"]
DEICTIC_WORDS = {"그거", "이거", "저거", "그것", "이것", "저것"}

_BARE_ORDINAL_RE = re.compile(r"^\\s*[가-힣0-9]+\\s*(?:번째|번)\\s*(?:상품)?\\s*(?:이요|요)?\\s*$")


def _is_bare_ordinal_utterance(text: str) -> bool:
    """
    True only for short ordinal-only utterances like "1번", "첫번째", "2번이요".

    This prevents misrouting queries like "1번 상품 가격 알려줘" into selection clicks.
    """
    if not text:
        return False
    if extract_ordinal_index(text) is None:
        return False
    return bool(_BARE_ORDINAL_RE.match(text))


def _extract_selection_target(text: str) -> str:
    target = text
    for kw in SELECTION_TRIGGERS:
        target = target.replace(kw, "").strip()
    for kw in FILLER_WORDS:
        target = target.replace(kw, "").strip()
    return target


def _is_ordinal_target(target: str) -> bool:
    if not target:
        return False
    return extract_ordinal_index(target) is not None


def _build_nth_result_selector(
    product_list: Optional[str],
    product_item: Optional[str],
    ordinal_index: int,
) -> Optional[str]:
    """Build a selector that targets the N-th product entry on the search page."""
    if ordinal_index is None or ordinal_index < 0:
        return None
    nth = ordinal_index + 1

    # Prefer selectors like: li[...] a[...]
    if product_item and product_item.startswith("li") and " " in product_item:
        first, rest = product_item.split(" ", 1)
        return f"{first}:nth-of-type({nth}) {rest}"

    # Fallbacks (may be less precise depending on DOM structure)
    if product_list:
        return f"{product_list}:nth-of-type({nth})"
    if product_item:
        return f"{product_item}:nth-of-type({nth})"

    return None


class SearchSelectRule(BaseRule):
    """검색 결과 페이지 선택 규칙"""

    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not current_url:
            return None

        page_type = get_page_type(current_url)
        if page_type != "search":
            return None

        # Also allow ordinal-only utterances like "1번" on search pages.
        has_explicit_select = any(kw in text for kw in SELECTION_TRIGGERS)
        has_bare_ordinal = _is_bare_ordinal_utterance(text)
        if not has_explicit_select and not has_bare_ordinal:
            return None

        if current_site is None:
            current_site = get_current_site(current_url)

        target = _extract_selection_target(text)

        if target:
            if target in DEICTIC_WORDS:
                return None

            # Ordinal selection: click the N-th product without requiring extracted search_results.
            if _is_ordinal_target(target):
                ordinal_index = extract_ordinal_index(target)
                product_item = current_site.get_selector("search", "product_item") if current_site else None
                product_list = current_site.get_selector("search", "product_list") if current_site else None
                target_selector = (
                    _build_nth_result_selector(product_list, product_item, ordinal_index)
                    if ordinal_index is not None
                    else None
                )
                if not target_selector:
                    return None

                commands = [
                    build_click_command(target_selector, f"검색 결과 {ordinal_index + 1}번째 상품 선택"),
                    GeneratedCommand(
                        tool_name="wait_for_new_page",
                        arguments={"timeout_ms": 1500, "focus": True},
                        description="detect new tab and focus",
                    ),
                    build_wait_command(1500, "상품 페이지 로딩 대기"),
                ]
                _append_detail_extract(commands, current_site, current_url)
                return RuleResult(
                    matched=True,
                    commands=commands,
                    response_text=f"{ordinal_index + 1}번째 상품을 선택합니다.",
                    rule_name="search_select",
                )

            commands = [
                build_click_text_command(target, f"검색 결과에서 '{target}' 선택"),
                GeneratedCommand(
                    tool_name="wait_for_new_page",
                    arguments={"timeout_ms": 1500, "focus": True},
                    description="detect new tab and focus",
                ),
                build_wait_command(1500, "상품 페이지 로딩 대기"),
            ]
            _append_detail_extract(commands, current_site, current_url)
            return RuleResult(
                matched=True,
                commands=commands,
                response_text=f"검색 결과에서 '{target}'을 선택합니다.",
                rule_name="search_select"
            )

        selector = None
        if current_site:
            selector = current_site.get_selector("search", "product_item")

        if selector:
            commands = [
                build_click_command(selector, "검색 결과 첫 상품 선택"),
                GeneratedCommand(
                    tool_name="wait_for_new_page",
                    arguments={"timeout_ms": 1500, "focus": True},
                    description="detect new tab and focus",
                ),
                build_wait_command(1500, "상품 페이지 로딩 대기"),
            ]
            _append_detail_extract(commands, current_site, current_url)
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="검색 결과에서 첫 상품을 선택합니다.",
                rule_name="search_select"
            )

        return None


def _append_detail_extract(
    commands: list[GeneratedCommand],
    current_site,
    current_url: str,
):
    if current_site is None and current_url:
        current_site = get_current_site(current_url)

    if not current_site:
        return

    detail_cmd = build_product_extract_command_for_site(current_site, current_url=current_url)
    if not detail_cmd:
        return

    commands.append(
        GeneratedCommand(
            tool_name=detail_cmd.tool_name,
            arguments=detail_cmd.arguments,
            description=detail_cmd.description or "extract product details",
        )
    )
