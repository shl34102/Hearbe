"""
Selection helpers for applying recent search results to user requests.
"""

from typing import Optional

from core.interfaces import LLMResponse, MCPCommand, SessionState
from core.korean_numbers import extract_ordinal_index
from .selection_intent import is_selection_request, is_ranking_query
from ...sites.site_manager import get_site_manager, get_current_site, get_selector, get_page_type


def select_from_results(
    user_text: str,
    session: Optional[SessionState]
) -> Optional[LLMResponse]:
    if not session or not session.context:
        return None
    results = session.context.get("search_results")
    if not isinstance(results, list) or not results:
        return None
    current_url = session.current_url or ""
    if current_url and get_page_type(current_url) != "search":
        return None

    target = user_text.strip().lower()
    if not target:
        return None

    if is_ranking_query(target):
        return None
    if not is_selection_request(target):
        return None
    ordinal_index = extract_ordinal_index(target)
    if ordinal_index is not None:
        if 0 <= ordinal_index < len(results):
            item = results[ordinal_index] if isinstance(results[ordinal_index], dict) else {}
            name = item.get("name") or item.get("title") or item.get("product_name")
            if name:
                session.context["last_mentioned_product"] = name
            commands = _build_click_nth_result_commands(session, ordinal_index)
            if not commands:
                if name:
                    commands = [
                        MCPCommand(
                            tool_name="click_text",
                            arguments={"text": name},
                            description=f"search result click '{name}'"
                        ),
                        MCPCommand(
                            tool_name="wait_for_new_page",
                            arguments={"timeout_ms": 1500, "focus": True},
                            description="detect new tab and focus"
                        ),
                        MCPCommand(
                            tool_name="wait",
                            arguments={"ms": 1500},
                            description="wait for product page"
                        )
                    ]
            if commands:
                return LLMResponse(
                    text=f"{ordinal_index + 1}번째 상품을 선택합니다.",
                    commands=commands,
                    requires_flow=False,
                    flow_type=None
                )

    matched_name = None
    matched_index = None
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("title") or item.get("product_name")
        if not name:
            continue
        name_lower = name.lower()
        if target in name_lower or name_lower in target:
            matched_name = name
            matched_index = idx
            break

    if not matched_name:
        return None
    session.context["last_mentioned_product"] = matched_name

    commands = _build_click_nth_result_commands(session, matched_index) if matched_index is not None else None
    if not commands:
        commands = [
            MCPCommand(
                tool_name="click_text",
                arguments={"text": matched_name},
                description=f"search result click '{matched_name}'"
            ),
            MCPCommand(
                tool_name="wait_for_new_page",
                arguments={"timeout_ms": 1500, "focus": True},
                description="detect new tab and focus"
            ),
            MCPCommand(
                tool_name="wait",
                arguments={"ms": 1500},
                description="wait for product page"
            )
        ]

    return LLMResponse(
        text=f"검색 결과에서 '{matched_name}'을 선택합니다.",
        commands=commands,
        requires_flow=False,
        flow_type=None
    )


def _build_click_nth_result_commands(
    session: Optional[SessionState],
    ordinal_index: int
) -> Optional[list[MCPCommand]]:
    if not session:
        return None

    # Prefer navigating by extracted product URL when available.
    # This avoids brittle selectors like `:nth-of-type(...)` that often break on Coupang.
    ctx = getattr(session, "context", {}) or {}
    results = ctx.get("search_results")
    if isinstance(results, list) and 0 <= ordinal_index < len(results):
        item = results[ordinal_index] if isinstance(results[ordinal_index], dict) else {}
        url = (item.get("url") or item.get("detail_url") or item.get("link") or "").strip() if isinstance(item, dict) else ""
        if url:
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = "https://www.coupang.com" + url
            commands = [
                MCPCommand(
                    tool_name="goto",
                    arguments={"url": url},
                    description=f"navigate to search result #{ordinal_index + 1}",
                ),
                MCPCommand(
                    tool_name="wait",
                    arguments={"ms": 1500},
                    description="wait for product page",
                ),
            ]
            return commands

    current_url = session.current_url or ""
    site = None
    if session.current_site:
        site = get_site_manager().get_site(session.current_site)
    if not site and current_url:
        site = get_current_site(current_url)

    selectors = {}
    if site:
        page = site.get_page_selectors("search")
        selectors = page.selectors if page and page.selectors else {}

    product_list = (
        selectors.get("product_list")
        or (get_selector(current_url, "product_list") if current_url else None)
    )
    product_item = (
        selectors.get("product_item")
        or (get_selector(current_url, "product_item") if current_url else None)
    )

    target_selector = None
    if product_item and product_item.startswith("li") and " " in product_item:
        first, rest = product_item.split(" ", 1)
        target_selector = f"{first}:nth-of-type({ordinal_index + 1}) {rest}"
    elif product_list:
        target_selector = f"{product_list}:nth-of-type({ordinal_index + 1})"
    elif product_item:
        target_selector = f"{product_item}:nth-of-type({ordinal_index + 1})"

    if not target_selector:
        return None

    commands = [
        MCPCommand(
            tool_name="click",
            arguments={"selector": target_selector},
            description=f"click search result #{ordinal_index + 1}"
        ),
        MCPCommand(
            tool_name="wait_for_new_page",
            arguments={"timeout_ms": 1500, "focus": True},
            description="detect new tab and focus"
        ),
        MCPCommand(
            tool_name="wait",
            arguments={"ms": 1500},
            description="wait for product page"
        )
    ]

    return commands
