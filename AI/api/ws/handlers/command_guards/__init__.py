# -*- coding: utf-8 -*-
"""
Platform command guards.

This package centralizes command-level safety guards and platform-specific
restrictions so command_pipeline has a single entry point.
"""

import logging
from typing import List

from services.llm.sites.site_manager import get_current_site

from .coupang import apply_coupang_guards
from .hearbe import apply_hearbe_guards

logger = logging.getLogger(__name__)


def apply_platform_guards(commands: List, current_url: str) -> List:
    """
    Apply platform command guards in a single place.

    Order:
    1) Coupang guards (includes pre-navigation + orderdetail cancel scope).
    2) Hearbe guards (hearbe-only restrictions).
    """
    if not commands:
        return commands

    guarded = apply_coupang_guards(commands, current_url)
    site = get_current_site(current_url) if current_url else None
    site_id = getattr(site, "site_id", "") if site else ""

    if site_id == "hearbe":
        guarded = apply_hearbe_guards(guarded, current_url)

    return guarded


__all__ = ["apply_platform_guards"]

