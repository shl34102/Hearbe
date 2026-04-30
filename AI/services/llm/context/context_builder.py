"""
LLM prompt context builder.
"""

from typing import Dict, List, Any, Optional

from .context_models import PageContext, get_page_context
from .context_selectors import (
    select_search_results,
    select_product_detail,
    select_cart_items,
    select_order_detail,
    select_order_list,
    select_order_history_recommendations,
)
from .context_prompts import build_system_prompt


class ContextBuilder:
    """Build LLM messages with contextual prompt."""

    def build_messages(
        self,
        user_text: str,
        current_url: str,
        conversation_history: List[Dict[str, str]] = None,
        page_context: PageContext = None,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        search_results = select_search_results(session_context, conversation_history)
        product_detail = select_product_detail(session_context, conversation_history)
        cart_items = select_cart_items(session_context, conversation_history)
        order_detail = select_order_detail(session_context, conversation_history)
        order_list = select_order_list(session_context, conversation_history)
        order_history_recommendations = select_order_history_recommendations(session_context, conversation_history)
        previous_url = session_context.get("previous_url") if session_context else None
        login_method_active = session_context.get("login_method_active") if session_context else None

        system_prompt = build_system_prompt(
            current_url=current_url,
            page_context=page_context,
            search_results=search_results,
            product_detail=product_detail,
            cart_items=cart_items,
            order_detail=order_detail,
            order_list=order_list,
            order_history_recommendations=order_history_recommendations,
            previous_url=previous_url,
            login_method_active=login_method_active,
        )

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append(
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                )

        messages.append({"role": "user", "content": user_text})
        return messages


__all__ = ["ContextBuilder", "PageContext", "get_page_context"]
