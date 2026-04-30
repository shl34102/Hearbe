# -*- coding: utf-8 -*-
"""
Common command pattern detection.
"""

from __future__ import annotations

from .utils import compact_text, get_args, get_tool_name


def is_order_cancel_command(cmd) -> bool:
    """
    Heuristic: treat any command that looks like an "order cancel" action as restricted.

    This intentionally favors safety: if we are not on the correct page, we drop it.
    """
    tool = get_tool_name(cmd)
    args = get_args(cmd)

    if tool == "click_text":
        text = compact_text(str(args.get("text", "") or ""))
        return ("주문" in text and "취소" in text) or ("order" in text.lower() and "cancel" in text.lower())

    if tool in ("click", "click_element"):
        selector = compact_text(str(args.get("selector", "") or ""))
        return ("주문" in selector and "취소" in selector) or ("order" in selector.lower() and "cancel" in selector.lower())

    return False


__all__ = ["is_order_cancel_command"]

