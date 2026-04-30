# -*- coding: utf-8 -*-
"""
LLM error handler with pluggable strategies.
"""

from typing import List

from .llm_errors import LLMError
from .decisions import ErrorHandlingDecision
from .strategies.base import ErrorStrategy
from .strategies.client_errors import ClientErrorStrategy
from .strategies.parse_errors import ParseErrorStrategy


class LLMErrorHandler:
    """Routes LLM errors to strategies."""

    def __init__(self):
        self._strategies: List[ErrorStrategy] = [
            ClientErrorStrategy(),
            ParseErrorStrategy(),
        ]

    def handle(self, error: LLMError, attempt: int) -> ErrorHandlingDecision:
        for strategy in self._strategies:
            if strategy.can_handle(error):
                return strategy.handle(error, attempt)
        return ErrorHandlingDecision(
            retry=False,
            fallback_text="요청을 처리할 수 없습니다. 다시 말씀해 주세요.",
            error=error.message,
        )
