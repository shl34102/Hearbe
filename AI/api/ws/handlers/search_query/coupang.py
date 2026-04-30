# -*- coding: utf-8 -*-
"""
Coupang-specific search query handler.
"""

from .common import SearchQueryHandler as CommonSearchQueryHandler


class CoupangSearchQueryHandler(CommonSearchQueryHandler):
    """
    Currently identical to common search behavior.
    Keep this class for Coupang-specific overrides.
    """


__all__ = ["CoupangSearchQueryHandler"]
