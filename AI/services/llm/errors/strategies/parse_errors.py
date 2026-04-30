# -*- coding: utf-8 -*-
"""
Parse error strategy.
"""

from ..llm_errors import LLMError, LLMParseError
from ..decisions import ErrorHandlingDecision
from ..tts_messages import PARSE_ERROR_TTS, FALLBACK_TTS
from .base import ErrorStrategy


class ParseErrorStrategy(ErrorStrategy):
    """Handle JSON/schema parse errors."""

    _retryable = {
        "json_parse",
        "schema_error",
    }

    def can_handle(self, error: LLMError) -> bool:
        return isinstance(error, LLMParseError)

    def handle(self, error: LLMError, attempt: int) -> ErrorHandlingDecision:
        message = PARSE_ERROR_TTS.get(error.error_type, FALLBACK_TTS)
        if error.error_type in self._retryable and attempt == 0:
            return ErrorHandlingDecision(
                retry=True,
                retry_delay_ms=200,
                fallback_text=message,
                error=error.message,
            )
        return ErrorHandlingDecision(
            retry=False,
            fallback_text=message,
            error=error.message,
        )
