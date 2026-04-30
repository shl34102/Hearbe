# -*- coding: utf-8 -*-
"""
Client/API error strategy.
"""

from ..llm_errors import LLMError, LLMClientError
from ..decisions import ErrorHandlingDecision
from ..tts_messages import CLIENT_ERROR_TTS, FALLBACK_TTS
from .base import ErrorStrategy


class ClientErrorStrategy(ErrorStrategy):
    """Handle network/API errors."""

    _retryable = {
        "timeout",
        "network_error",
        "rate_limit",
        "server_error",
        "empty_response",
    }
    _no_retry = {
        "client_error",
        "auth_error",
    }

    def can_handle(self, error: LLMError) -> bool:
        return isinstance(error, LLMClientError)

    def handle(self, error: LLMError, attempt: int) -> ErrorHandlingDecision:
        message = CLIENT_ERROR_TTS.get(error.error_type, FALLBACK_TTS)
        if error.error_type in self._retryable and attempt == 0:
            return ErrorHandlingDecision(
                retry=True,
                retry_delay_ms=500,
                fallback_text=message,
                error=error.message,
            )
        if error.error_type in self._no_retry:
            return ErrorHandlingDecision(
                retry=False,
                fallback_text=message,
                error=error.message,
            )
        return ErrorHandlingDecision(
            retry=False,
            fallback_text=message,
            error=error.message,
        )
