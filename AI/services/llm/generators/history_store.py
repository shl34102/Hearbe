# -*- coding: utf-8 -*-
"""
Local conversation history store.
"""

from typing import Dict, List


class HistoryStore:
    """Keeps a bounded local history for LLM context."""

    def __init__(self, max_items: int = 10):
        self._max_items = max_items
        self._history: List[Dict[str, str]] = []

    def add_user(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._truncate()

    def add_assistant(self, text: str) -> None:
        self._history.append({"role": "assistant", "content": text})
        self._truncate()

    def get(self) -> List[Dict[str, str]]:
        return self._history.copy()

    def clear(self) -> None:
        self._history = []

    def _truncate(self) -> None:
        if len(self._history) > self._max_items:
            self._history = self._history[-self._max_items:]
