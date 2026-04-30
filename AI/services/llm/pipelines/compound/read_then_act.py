# -*- coding: utf-8 -*-
"""
Compound pipeline: read then act.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Optional, Tuple

from core.interfaces import LLMResponse, SessionState
from services.llm.pipelines.shared.intent_guard import has_action_intent


READ_HINT_PATTERNS = (
    r"(읽어|읽고|읽기)",
    r"(보여|보여줘)",
    r"(들려|들려줘)",
    r"(알려|알려줘)",
    r"(요약)",
    r"(확인)",
    r"(설명)",
)


ReadHandler = Callable[[str, Optional[SessionState], bool], Optional[LLMResponse]]


def handle_read_then_act(
    user_text: str,
    session: Optional[SessionState],
    read_handlers: Iterable[ReadHandler],
) -> Optional[Tuple[LLMResponse, str]]:
    if not session or not session.context:
        return None
    text = (user_text or "").strip()
    if not text:
        return None
    if not has_action_intent(text):
        return None
    if not any(re.search(pattern, text) for pattern in READ_HINT_PATTERNS):
        return None

    for handler in read_handlers:
        response = handler(text, session, True)
        if response and response.text:
            return response, handler.__name__

    return None


__all__ = ["handle_read_then_act"]
