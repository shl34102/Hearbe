# -*- coding: utf-8 -*-
"""
Error handling decisions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ErrorHandlingDecision:
    retry: bool = False
    retry_delay_ms: int = 0
    fallback_text: str = "요청을 처리할 수 없습니다. 다시 말씀해 주세요."
    error: Optional[str] = None
