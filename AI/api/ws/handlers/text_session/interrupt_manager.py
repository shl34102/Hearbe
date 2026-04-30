# -*- coding: utf-8 -*-
"""
Interrupt epoch tracking per session.
"""

from typing import Dict


class InterruptManager:
    def __init__(self):
        self._epochs: Dict[str, int] = {}

    def create_session(self, session_id: str) -> None:
        self._epochs[session_id] = 0

    def cleanup_session(self, session_id: str) -> None:
        self._epochs.pop(session_id, None)

    def interrupt(self, session_id: str) -> int:
        self._epochs[session_id] = self._epochs.get(session_id, 0) + 1
        return self._epochs[session_id]

    def get_epoch(self, session_id: str) -> int:
        return self._epochs.get(session_id, 0)

    def is_interrupted(self, session_id: str, epoch: int) -> bool:
        return self._epochs.get(session_id, 0) != epoch
