# -*- coding: utf-8 -*-
"""
LLM error types and exceptions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMErrorInfo:
    error_type: str
    message: str
    exception: Optional[Exception] = None


class LLMError(Exception):
    """Base LLM error."""

    def __init__(self, error_type: str, message: str, exception: Optional[Exception] = None):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.exception = exception


class LLMClientError(LLMError):
    """LLM client/network/API error."""


class LLMParseError(LLMError):
    """LLM response parse error."""
