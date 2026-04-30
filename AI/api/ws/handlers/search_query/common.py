# -*- coding: utf-8 -*-
"""
Search query handler: processes search result queries and insights.

Handles:
- Search result reading ("전체 읽어줘", "n개 더 읽어줘")
- Item-specific queries ("1번 상품 가격은?", "2번 할인율은?")
- Search insights ("가장 할인율 높은 상품", "내일 도착하는 상품만")
"""

import logging
import re
from typing import Optional, Tuple

from services.llm.generators.tts_pages.search import (
    build_search_list_tts,
    MORE_PROMPT_NUMBER,
    NO_DISCOUNT_INFO,
    NO_PRICE_INFO,
    NO_TOMORROW_ITEMS,
    NO_FREE_SHIPPING,
    format_highest_discount,
    format_lowest_price,
)
from ...search.search_insights import (
    get_name,
    get_price_text,
    get_discount_text,
    get_delivery_text,
    get_rating_text,
    is_free_shipping,
    extract_ordinal_index,
    find_lowest_price_item,
    find_highest_discount_item,
    filter_tomorrow_items,
    filter_free_shipping_items,
)

logger = logging.getLogger(__name__)


class SearchQueryHandler:
    """
    Handles search-related queries.

    Processes user requests about search results without involving LLM,
    providing fast responses for common search operations.
    """

    def __init__(self, session_manager, sender):
        """
        Initialize search query handler.

        Args:
            session_manager: Session manager instance
            sender: WebSocket sender instance
        """
        self._session = session_manager
        self._sender = sender

    async def handle_query(self, session_id: str, text: str, session) -> bool:
        """
        Handle search-related query.

        Args:
            session_id: Session ID
            text: User input text
            session: Session state

        Returns:
            True if query was handled, False otherwise
        """
        normalized = text.strip().lower()
        if not normalized:
            return False

        # Insight queries are deterministic and should not require LLM.
        if (
            self._is_highest_discount_request(normalized)
            or self._is_lowest_price_request(normalized)
            or self._is_tomorrow_delivery_request(normalized)
            or self._is_free_shipping_list_request(normalized)
        ):
            return await self._handle_insight_query(session_id, normalized, session)

        # Attribute-level Q&A can also be implemented here, but keep it routed to LLM for now
        # until wording coverage is validated (price/discount/delivery/rating/free-shipping).
        if self._is_attribute_query(normalized):
            return False

        if not self._is_read_request(normalized):
            return False

        return await self._handle_read_query(session_id, normalized, session)

    async def _handle_insight_query(
        self,
        session_id: str,
        text: str,
        session
    ) -> bool:
        """
        Handle insight queries: filtering, ranking, analysis.

        Examples:
        - "가장 할인율 높은 상품 알려줘"
        - "내일 도착하는 상품만 보여줘"
        - "무료배송 상품 목록"
        """
        results = self._get_active_results(session)
        if not results:
            return False

        normalized = text.strip().lower()
        if not normalized:
            return False

        # Highest discount
        if self._is_highest_discount_request(normalized):
            item, discount = find_highest_discount_item(results)
            if not item or discount is None:
                await self._sender.send_tts_response(session_id, NO_DISCOUNT_INFO)
                return True
            name = get_name(item)
            price = get_price_text(item)
            discount_text = get_discount_text(item)
            msg = format_highest_discount(name, discount_text, price)
            await self._sender.send_tts_response(session_id, msg)
            return True

        # Lowest price
        if self._is_lowest_price_request(normalized):
            item, _ = find_lowest_price_item(results)
            if not item:
                await self._sender.send_tts_response(session_id, NO_PRICE_INFO)
                return True
            name = get_name(item)
            price = get_price_text(item)
            msg = format_lowest_price(name, price)
            await self._sender.send_tts_response(session_id, msg)
            return True

        # Tomorrow delivery filter
        if self._is_tomorrow_delivery_request(normalized):
            filtered = filter_tomorrow_items(results)
            if not filtered:
                await self._sender.send_tts_response(session_id, NO_TOMORROW_ITEMS)
                return True
            self._session.set_context(session_id, "search_active_results", filtered)
            self._session.set_context(session_id, "search_active_label", "tomorrow")
            self._session.set_context(session_id, "search_read_index", 0)
            tts_text, next_index, has_more = build_search_list_tts(
                filtered,
                start_index=0,
                count=min(4, len(filtered)),
                include_total=True,
                more_prompt=MORE_PROMPT_NUMBER
            )
            self._session.set_context(session_id, "search_read_index", next_index)
            self._set_last_mentioned_from_index(session_id, filtered, next_index - 1)
            await self._sender.send_tts_response(session_id, tts_text)
            return True

        # Free shipping filter
        if self._is_free_shipping_list_request(normalized):
            filtered = filter_free_shipping_items(results)
            if not filtered:
                await self._sender.send_tts_response(session_id, NO_FREE_SHIPPING)
                return True
            self._session.set_context(session_id, "search_active_results", filtered)
            self._session.set_context(session_id, "search_active_label", "free_shipping")
            self._session.set_context(session_id, "search_read_index", 0)
            tts_text, next_index, has_more = build_search_list_tts(
                filtered,
                start_index=0,
                count=min(4, len(filtered)),
                include_total=True,
                more_prompt=MORE_PROMPT_NUMBER
            )
            self._session.set_context(session_id, "search_read_index", next_index)
            self._set_last_mentioned_from_index(session_id, filtered, next_index - 1)
            await self._sender.send_tts_response(session_id, tts_text)
            return True

        return False

    async def _handle_read_query(
        self,
        session_id: str,
        text: str,
        session
    ) -> bool:
        """
        Handle read queries: list reading only.

        Examples:
        - "전체 읽어줘"
        - "n개 더 읽어줘"
        """
        results = self._get_active_results(session)
        if not results:
            return False

        normalized = text.strip().lower()
        if not normalized:
            return False

        if self._is_plain_results_request(normalized):
            mode, count = "restart", 4
        else:
            if not self._is_read_request(normalized):
                return False
            mode, count = self._parse_read_request(normalized)
            if mode is None:
                return False

        total = len(results)
        start_index = self._session.get_context(session_id, "search_read_index", 0)

        # If results were just auto-announced, avoid re-reading immediately unless the user
        # explicitly requested a restart ("다시", "처음부터"). This reduces duplicate TTS spam.
        if self._was_recently_auto_announced(session_id, session) and start_index > 0:
            # Allow explicit "more" requests (e.g. "2개 더 읽어줘") even if auto-announcement
            # happened recently. Only dedupe vague "read the results" requests.
            if mode != "more" and not self._is_restart_read_request(normalized):
                await self._sender.send_tts_response(
                    session_id,
                    "방금 검색 결과를 읽어드렸어요. 몇 개 더 읽어드릴까요?",
                )
                return True

        if mode == "all":
            count = total
        elif mode == "restart":
            start_index = 0
            count = count or 4
        elif mode == "more":
            count = count or 4
        else:
            return False

        tts_text, next_index, has_more = build_search_list_tts(
            results,
            start_index=start_index,
            count=count,
            include_total=(mode == "all" and start_index == 0),
            more_prompt=MORE_PROMPT_NUMBER
        )
        self._session.set_context(session_id, "search_read_index", next_index)
        self._set_last_mentioned_from_index(session_id, results, next_index - 1)
        await self._sender.send_tts_response(session_id, tts_text)
        return True

    def _was_recently_auto_announced(self, session_id: str, session) -> bool:
        """
        True if the current search results were auto-read very recently.

        Used to dedupe when the user says "검색 결과 읽어줘" immediately after auto-extract.
        """
        try:
            if not session or not getattr(session, "context", None):
                return False
            ctx = session.context
            sig = ctx.get("search_results_signature")
            announced_sig = ctx.get("search_results_announced_signature")
            if not sig or not announced_sig or sig != announced_sig:
                return False
            ts = ctx.get("search_last_announce_ts")
            if not ts:
                return False
            import time

            return (time.time() - float(ts)) <= 20.0
        except Exception:
            return False

    @staticmethod
    def _is_restart_read_request(normalized: str) -> bool:
        compact = (normalized or "").replace(" ", "")
        return ("다시" in compact) or ("처음" in compact) or ("처음부터" in compact)

    def _get_active_results(self, session):
        """Get currently active search results from session."""
        if not session:
            return None
        results = session.context.get("search_active_results")
        if not results:
            results = session.context.get("search_results")
        if not isinstance(results, list) or not results:
            return None
        return results

    def _set_last_mentioned_product(self, session_id: str, item):
        name = get_name(item) if item else ""
        if name:
            self._session.set_context(session_id, "last_mentioned_product", name)

    def _set_last_mentioned_from_index(self, session_id: str, results, index: int):
        if not results or index is None:
            return
        if 0 <= index < len(results):
            self._set_last_mentioned_product(session_id, results[index])

    # ========================================================================
    # Pattern matching helpers
    # ========================================================================

    def _is_highest_discount_request(self, normalized: str) -> bool:
        """Check if user is asking for highest discount item."""
        if "할인" not in normalized:
            return False
        keywords = ["가장", "제일", "최대", "높", "많"]
        return any(k in normalized for k in keywords)

    def _is_lowest_price_request(self, normalized: str) -> bool:
        """Check if user is asking for lowest price item."""
        price_keywords = ["가격", "최저가", "저렴", "싼"]
        rank_keywords = ["가장", "제일", "최저", "낮", "싸"]
        return any(k in normalized for k in price_keywords) and any(k in normalized for k in rank_keywords)

    def _is_tomorrow_delivery_request(self, normalized: str) -> bool:
        """Check if user is asking for tomorrow delivery items."""
        if "내일" not in normalized:
            return False
        keywords = ["도착", "배송", "받"]
        return any(k in normalized for k in keywords)

    def _is_free_shipping_list_request(self, normalized: str) -> bool:
        """Check if user is asking for free shipping list."""
        if "무료" not in normalized or "배송" not in normalized:
            return False
        keywords = ["상품", "목록", "알려", "보여", "읽어"]
        return any(k in normalized for k in keywords)

    def _is_free_shipping_query(self, normalized: str) -> bool:
        """Check if user is asking about free shipping."""
        return "무료" in normalized and "배송" in normalized

    def _is_price_query(self, normalized: str) -> bool:
        """Check if user is asking about price."""
        return "가격" in normalized or "얼마" in normalized or "금액" in normalized

    def _is_discount_query(self, normalized: str) -> bool:
        """Check if user is asking about discount."""
        return "할인" in normalized

    def _is_delivery_query(self, normalized: str) -> bool:
        """Check if user is asking about delivery."""
        keywords = ["배송", "도착", "받"]
        return any(k in normalized for k in keywords)

    def _is_rating_query(self, normalized: str) -> bool:
        """Check if user is asking about rating."""
        keywords = ["평점", "별점", "점수", "몇점"]
        return any(k in normalized for k in keywords)

    def _is_attribute_query(self, normalized: str) -> bool:
        """Check if user is asking about a specific attribute."""
        return any(
            [
                self._is_price_query(normalized),
                self._is_discount_query(normalized),
                self._is_delivery_query(normalized),
                self._is_rating_query(normalized),
                self._is_free_shipping_query(normalized),
            ]
        )

    def _is_read_request(self, normalized: str) -> bool:
        """Check if user is asking to read results."""
        keywords = ["읽어", "읽어줘", "읽어주", "읽어줄래", "들려", "들려줘"]
        target = ["상품", "검색", "검색결과", "결과", "전체", "모든", "현재"]
        has_keywords = any(k in normalized for k in keywords)
        if not has_keywords:
            return False
        if any(t in normalized for t in target):
            return True
        # "처음부터/첫번째부터 다시 읽어줘"
        if ("처음" in normalized or "첫" in normalized) and ("부터" in normalized or "다시" in normalized):
            return True
        # Allow "n개 더 읽어줘" without target words when search results exist
        if "더" in normalized or re.search(r"\d+\s*개", normalized):
            return True
        return False

    def _is_plain_results_request(self, normalized: str) -> bool:
        """Handle plain '검색 결과' requests without explicit read verbs."""
        return "검색 결과" in normalized or "검색결과" in normalized

    def _parse_read_request(self, normalized: str) -> Tuple[Optional[str], Optional[int]]:
        """Parse read request mode and count."""
        if "전체" in normalized or "모든" in normalized:
            return "all", None
        if "처음" in normalized or "첫" in normalized:
            if "다시" in normalized or "부터" in normalized:
                return "restart", None
        if "더" in normalized:
            match = re.search(r"(\d+)\s*개", normalized)
            if match:
                return "more", int(match.group(1))
            return "more", None
        return None, None
