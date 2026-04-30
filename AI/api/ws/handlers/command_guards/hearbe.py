# -*- coding: utf-8 -*-
"""
Hearbe command guards.

Keep Hearbe context clean by dropping Coupang-only order cancel actions.
"""

import logging
from typing import List

from .patterns import is_order_cancel_command
from .utils import get_tool_name

logger = logging.getLogger(__name__)


def apply_hearbe_guards(commands: List, current_url: str) -> List:
    if not commands:
        return commands

    filtered = []
    removed = 0
    for cmd in commands:
        tool = get_tool_name(cmd)
        # Hearbe pages should not run Coupang extractors. Those are MCP-side extractors and will
        # produce misleading prompts / temp files if invoked on Hearbe URLs.
        if tool.startswith("extract"):
            removed += 1
            continue
        if is_order_cancel_command(cmd):
            removed += 1
            continue
        filtered.append(cmd)

    if removed:
        logger.info(
            "Command guard(hearbe): removed %d command(s) (extract/order-cancel)",
            removed,
        )
    return filtered


__all__ = ["apply_hearbe_guards"]
