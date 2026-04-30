# -*- coding: utf-8 -*-
"""
LLM generator facade.
"""

from typing import Dict, List, Any, Optional

from .response_generator import ResponseGenerator, LLMResult
from .tts_generator import TTSGenerator
from .llm_client import resolve_llm_api_key


class LLMGenerator:
    def __init__(self, api_key: str = None, model: str = "gpt-5-mini"):
        self._response = ResponseGenerator(api_key=api_key, model=model)
        self._tts = TTSGenerator()

    async def generate(
        self,
        user_text: str,
        current_url: str = "",
        page_type: Optional[str] = None,
        available_selectors: Optional[Dict[str, str]] = None,
        conversation_history: List[Dict[str, str]] = None,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        return await self._response.generate(
            user_text=user_text,
            current_url=current_url,
            page_type=page_type,
            available_selectors=available_selectors,
            conversation_history=conversation_history,
            session_context=session_context,
        )

    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        current_url: str = "",
    ) -> LLMResult:
        return await self._response.generate_with_messages(messages, current_url)

    def clear_history(self) -> None:
        self._response.clear_history()

    def get_history(self) -> List[Dict[str, str]]:
        return self._response.get_history()

    @property
    def tts(self) -> TTSGenerator:
        return self._tts


_generator_instance: Optional[LLMGenerator] = None


def get_llm_generator() -> LLMGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = LLMGenerator()
    return _generator_instance


__all__ = [
    "LLMGenerator",
    "LLMResult",
    "get_llm_generator",
    "resolve_llm_api_key",
]
