# -*- coding: utf-8 -*-
"""
Session history writer.
"""


class HistoryWriter:
    def __init__(self, session_manager):
        self._session = session_manager

    def add_user(self, session_id: str, text: str) -> None:
        if not self._session:
            return
        self._session.add_to_history(session_id, "user", text)

    def add_assistant(self, session_id: str, text: str) -> None:
        if not self._session:
            return
        self._session.add_to_history(session_id, "assistant", text)
