# -*- coding: utf-8 -*-
"""
Hearbe-specific search query handler.
"""

from .common import SearchQueryHandler as CommonSearchQueryHandler


class HearbeSearchQueryHandler(CommonSearchQueryHandler):
    """
    Currently identical to common search behavior.
    Keep this class for Hearbe-specific overrides.
    """


__all__ = ["HearbeSearchQueryHandler"]
