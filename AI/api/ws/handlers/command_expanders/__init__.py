# -*- coding: utf-8 -*-
"""
Command expansion helpers (multi-step command insertion).
"""

from typing import List

from .coupang_pre_navigation import expand_coupang_pre_navigation


def expand_pre_navigation_commands(commands: List, current_url: str) -> List:
    """
    Expand commands with site-specific pre-navigation logic.

    Designed to be extended with additional site modules.
    """
    if not commands:
        return commands
    commands = expand_coupang_pre_navigation(commands, current_url)
    return commands


__all__ = ["expand_pre_navigation_commands"]
