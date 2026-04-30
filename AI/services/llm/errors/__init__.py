# -*- coding: utf-8 -*-
"""
LLM error handling package.
"""

from .llm_errors import LLMError, LLMClientError, LLMParseError, LLMErrorInfo
from .decisions import ErrorHandlingDecision
from .error_handler import LLMErrorHandler
from .tts_messages import CLIENT_ERROR_TTS, PARSE_ERROR_TTS, FALLBACK_TTS

__all__ = [
    "LLMError",
    "LLMClientError",
    "LLMParseError",
    "LLMErrorInfo",
    "LLMErrorHandler",
    "ErrorHandlingDecision",
    "CLIENT_ERROR_TTS",
    "PARSE_ERROR_TTS",
    "FALLBACK_TTS",
]
