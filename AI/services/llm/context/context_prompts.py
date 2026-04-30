# -*- coding: utf-8 -*-
"""
Prompt construction utilities for LLM context.
"""

import json
from typing import Any, Dict, List, Optional

from ..sites.site_manager import get_site_manager
from .context_formatters import (
    format_commands,
    format_selectors,
    format_search_results_section,
    format_product_detail_section,
    format_cart_items_section,
    format_order_detail_section,
    format_order_list_section,
    format_order_history_recommendations_section,
    format_url_context,
)
from .context_models import PageContext, get_page_context


def _format_site_urls(site) -> str:
    if not site:
        return ""
    urls_dict = getattr(site, "urls", {}) or {}
    if not isinstance(urls_dict, dict) or not urls_dict:
        return ""

    # Keep commonly referenced URLs first, then list the rest (sorted) for platform-specific flows.
    preferred = ("home", "main", "login", "cart", "mypage")
    ordered_items = []
    seen = set()
    for key in preferred:
        url = urls_dict.get(key) or site.get_url(key)
        if url:
            ordered_items.append((key, url))
            seen.add(key)
    for key in sorted(urls_dict.keys()):
        if key in seen:
            continue
        url = urls_dict.get(key) or site.get_url(key)
        if url:
            ordered_items.append((key, url))

    if not ordered_items:
        return ""
    return "\n".join(["## Site URLs"] + [f"- {k}: {u}" for k, u in ordered_items])


def _build_login_constraints(site_id: str, page_type: str, login_method_active: Optional[str] = None) -> str:
    if page_type == "login":
        if site_id == "coupang":
            return (
                "## Login constraints\n"
                "- When the user expresses login intent, proceed with email + password (do not ask the method).\n"
                "- Default method is email + password.\n"
                "- Do NOT choose phone/OTP unless the user explicitly asks for phone login.\n"
                "- If the user asks for phone login, switch to the phone login tab and request the phone number (OTP is via SMS only).\n"
                "- After entering OTP, click otp_submit_button (e.g., #loginWithSmsCode) if available.\n"
                "- Prefer concrete actions over follow-up questions when selectors exist.\n"
                "- Use only tools from the Available commands list; do not invent tools like 'submit_login'.\n"
                "- To submit login, click the login button selector (e.g., login_button/submit_button or button[type='submit']).\n"
            )

        if site_id == "hearbe":
            return (
                "## Login constraints\n"
                "- This is Hearbe (first-party) login. Use email + password only.\n"
                "- Prefer using provided selectors (email_input, password_input, login_button/submit_button).\n"
                "- If credentials are already filled by the browser, just click submit.\n"
                "- Use only tools from the Available commands list; do not invent tools.\n"
            )

        return (
            "## Login constraints\n"
            "- Use email + password by default.\n"
            "- Use only tools from the Available commands list.\n"
        )

    # Not on login page: if user wants to login, navigate to login page first
    return ""


def build_system_prompt(
    current_url: str,
    page_context: Optional[PageContext] = None,
    search_results: List[Any] = None,
    product_detail: Optional[Dict[str, Any]] = None,
    cart_items: List[Dict[str, Any]] = None,
    order_detail: Optional[Dict[str, Any]] = None,
    order_list: Optional[Any] = None,
    order_history_recommendations: Optional[List[Dict[str, Any]]] = None,
    previous_url: Optional[str] = None,
    login_method_active: Optional[str] = None,
) -> str:
    """Build the LLM system prompt for the current request."""
    if page_context is None:
        site = get_site_manager().get_site_by_url(current_url)
        page_context = get_page_context(current_url, site)
    else:
        site = get_site_manager().get_site_by_url(current_url)

    commands_doc = format_commands()
    selectors_doc = format_selectors(page_context.selectors)
    search_results_section = (
        format_search_results_section(search_results)
        if page_context.page_type == "search"
        else ""
    )
    product_detail_section = (
        format_product_detail_section(product_detail)
        if page_context.page_type == "product"
        else ""
    )
    cart_items_section = (
        format_cart_items_section(cart_items, current_url)
        if page_context.page_type == "cart"
        else ""
    )
    order_detail_section = (
        format_order_detail_section(order_detail)
        if page_context.page_type == "orderdetail"
        else ""
    )
    order_list_section = (
        format_order_list_section(order_list)
        if page_context.page_type == "orderlist"
        else ""
    )
    order_history_recommendations_section = (
        format_order_history_recommendations_section(order_history_recommendations)
        if page_context.page_type == "order_history"
        else ""
    )
    url_context_section = format_url_context(current_url, previous_url)
    site_urls_section = _format_site_urls(site)
    site_id = getattr(site, "site_id", "") if site else ""
    login_constraints = _build_login_constraints(site_id, page_context.page_type, login_method_active)

    output_example = json.dumps(
        {
            "response": "short message",
            "commands": [
                {"tool_name": "tool", "arguments": {}, "description": "description"}
            ],
        },
        ensure_ascii=True,
        indent=2,
    )
    return f"""You are a shopping assistant that converts user requests into MCP tool calls.

## Current context
- Site: {page_context.site_name}
- Page type: {page_context.page_type}
- URL: {current_url}
- Available actions: {', '.join(page_context.available_actions)}
{url_context_section}

{site_urls_section}

## Available commands
{commands_doc}

## Page selectors
{selectors_doc}

{search_results_section}
{product_detail_section}
{cart_items_section}
{order_detail_section}
{order_list_section}
{order_history_recommendations_section}
{login_constraints}
## Rules
1. Respond with JSON only.
2. Commands are executed in order.
3. If a selector is uncertain, use click_text.
4. Add wait before or after navigation when needed.
5. You are an action executor. If the user requests any action (navigate, click, login, search, add to cart, etc.), you MUST generate commands. Never ask clarifying questions — pick the most likely action and execute it. Only return empty commands when answering a purely informational question that can be fully answered from the provided context data above (e.g. reading product info, price, search results).
6. If the user wants to navigate to a site or page, use goto with the URL from Site URLs, or click the appropriate link/button.
7. If the user wants to login and is NOT on the login page, navigate to the login page first.
8. Do not include URLs in the response text.
9. Keep response text under 2 sentences. Describe only what you are doing.
10. If the user asks to logout, click the top logout button only (use selector 'logout' if available, otherwise click_text for '\ub85c\uadf8\uc544\uc6c3') and respond only with '\ub85c\uadf8\uc544\uc6c3 \ub418\uc5c8\uc2b5\ub2c8\ub2e4.'.

## Output format
{output_example}
"""
