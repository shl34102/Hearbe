# -*- coding: utf-8 -*-
"""
Search query handler router.

Delegates to site-specific handlers (common, coupang, hearbe).
"""

from services.llm.sites.site_manager import get_current_site

from .search_query.common import SearchQueryHandler as CommonSearchQueryHandler
from .search_query.coupang import CoupangSearchQueryHandler
from .search_query.hearbe import HearbeSearchQueryHandler


class SearchQueryHandler:
    def __init__(self, session_manager, sender):
        self._session = session_manager
        self._common = CommonSearchQueryHandler(session_manager, sender)
        self._coupang = CoupangSearchQueryHandler(session_manager, sender)
        self._hearbe = HearbeSearchQueryHandler(session_manager, sender)

    async def handle_query(self, session_id: str, text: str, session) -> bool:
        handler = self._pick_handler(session)
        return await handler.handle_query(session_id, text, session)

    def _pick_handler(self, session):
        if not session:
            return self._common
        url = getattr(session, "current_url", "") or ""
        site = get_current_site(url) if url else None
        site_id = getattr(site, "site_id", "") if site else ""
        if site_id == "hearbe":
            return self._hearbe
        if site_id == "coupang":
            return self._coupang
        return self._common


__all__ = ["SearchQueryHandler"]
