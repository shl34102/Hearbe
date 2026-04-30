# -*- coding: utf-8 -*-
"""
LLM fallback response helper.

When LLM cannot produce tool commands, return a safe, user-facing response.
"""

from typing import Optional

from core.interfaces import LLMResponse


def build_llm_fallback_response(
    user_text: str,
    response_text: Optional[str]
) -> Optional[LLMResponse]:
    """
    Build a fallback response when LLM returns no commands.

    Prefer LLM-provided response text. If missing, use a generic clarification.
    """
    if response_text:
        return LLMResponse(
            text=response_text,
            commands=[],
            requires_flow=False,
            flow_type=None
        )

    # Generic clarification if LLM response is empty
    return LLMResponse(
        text="정확히 어떤 동작을 원하시는지 말씀해 주세요.",
        commands=[],
        requires_flow=False,
        flow_type=None
    )
