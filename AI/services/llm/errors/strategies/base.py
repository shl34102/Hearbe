# -*- coding: utf-8 -*-
"""
Error strategy base.
"""

from abc import ABC, abstractmethod

from ..llm_errors import LLMError
from ..decisions import ErrorHandlingDecision


class ErrorStrategy(ABC):
    @abstractmethod
    def can_handle(self, error: LLMError) -> bool:
        raise NotImplementedError

    @abstractmethod
    def handle(self, error: LLMError, attempt: int) -> ErrorHandlingDecision:
        raise NotImplementedError
