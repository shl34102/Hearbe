# -*- coding: utf-8 -*-
"""
LLM-based TTS response generator.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from services.llm.errors.llm_errors import LLMClientError
from .llm_client import LLMClient, resolve_llm_api_key

logger = logging.getLogger(__name__)


def _truncate_value(value: Any, limit: int = 120) -> Any:
    if isinstance(value, str):
        return value if len(value) <= limit else f"{value[:limit]}...<truncated>"
    return value


def _summarize_commands(commands: List[Any]) -> List[Dict[str, Any]]:
    summary = []
    for cmd in commands or []:
        tool_name = getattr(cmd, "tool_name", "") or ""
        arguments = getattr(cmd, "arguments", None) or {}
        safe_args = {}
        for key, value in arguments.items():
            safe_args[key] = _truncate_value(value)
        summary.append({"tool": tool_name, "args": safe_args})
    return summary


def _compact_product_detail(detail: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(detail, dict):
        return {}
    compact = {
        "name": detail.get("name") or detail.get("title") or detail.get("product_name") or "",
        "price": detail.get("price") or detail.get("final_price") or detail.get("sale_price") or "",
        "original_price": detail.get("original_price") or "",
        "discount_rate": detail.get("discount_rate") or "",
        "delivery": detail.get("delivery") or detail.get("rocket_delivery") or "",
        "options": detail.get("options") or {},
    }
    options_list = detail.get("options_list")
    if isinstance(options_list, dict):
        selected = []
        for key, items in options_list.items():
            if not isinstance(items, list):
                continue
            picked = next((item for item in items if isinstance(item, dict) and item.get("selected")), None)
            if picked:
                selected.append({"key": key, "name": picked.get("name"), "price": picked.get("price")})
        if selected:
            compact["selected_options"] = selected
    return compact


class TTSTextGenerator:
    """
    Generate a concise spoken response for TTS using a separate LLM request.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = resolve_llm_api_key(api_key)
        self.model = model or os.environ.get("LLM_TTS_MODEL", "gpt-5-mini")
        self.base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        try:
            self.max_tokens = int(os.environ.get("LLM_TTS_MAX_TOKENS", "512"))
        except ValueError:
            self.max_tokens = 512
        try:
            timeout_seconds = float(os.environ.get("LLM_TTS_TIMEOUT_SECONDS", "20"))
        except ValueError:
            timeout_seconds = 20.0
        self._client = LLMClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=self.max_tokens,
            timeout_seconds=timeout_seconds,
        )

    async def generate(
        self,
        user_text: str,
        current_url: str = "",
        page_type: Optional[str] = None,
        commands: Optional[List[Any]] = None,
        fallback_text: str = "",
        session_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not user_text:
            return fallback_text or ""

        payload = {
            "user_text": user_text,
            "current_url": current_url or "",
            "page_type": page_type or "",
            "commands": _summarize_commands(commands or []),
        }
        if session_context:
            context_hint = {
                "cart_items_count": len(session_context.get("cart_items") or []),
                "search_results_count": len(session_context.get("search_results") or []),
                "previous_url": session_context.get("previous_url") or "",
            }
            product_detail = session_context.get("product_detail")
            if isinstance(product_detail, dict):
                context_hint["product_detail"] = _compact_product_detail(product_detail)
            payload["context_hint"] = context_hint

        system_prompt = (
            "You are a Korean shopping voice assistant. "
            "Generate a concise, natural spoken response in Korean. "
            "Use 1-2 short sentences. "
            "Do not include URLs or JSON. "
            "If commands are present, briefly explain the action. "
            "If the request is unclear, ask a brief clarification."
        )
        user_prompt = json.dumps(payload, ensure_ascii=False)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            content = await self._client.request(
                messages=messages,
                current_url=current_url,
                text_len=len(user_text),
                label="tts",
                response_format=None,
                max_tokens=self.max_tokens,
            )
            return (content or "").strip()
        except LLMClientError as e:
            logger.warning("TTS LLM error: %s", e)
        except Exception as e:
            logger.warning("TTS LLM failure: %s", e)
        return fallback_text or ""


__all__ = ["TTSTextGenerator"]
