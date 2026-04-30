# -*- coding: utf-8 -*-
"""
Shared intent guard helpers for read pipelines.
"""

import re


ACTION_PATTERNS = (
    r"(담아|담기|추가)",
    r"(삭제|제거|빼)",
    r"(변경|수정|바꿔|바꾸)",
    r"(선택|해제|체크)",
    r"(이동|이동해|이동하기)",
    r"(검색해|검색하기|검색해줘)",
    r"(결제|주문|구매).*(해|하기|진행)",
    r"(바로구매)",
    r"(클릭|눌러)",
    r"(수량).*(변경|늘려|줄여|바꿔)",
)


def has_action_intent(text: str) -> bool:
    if not text:
        return False
    normalized = re.sub(r"\s+", "", text)
    return any(re.search(pattern, normalized) for pattern in ACTION_PATTERNS)


__all__ = ["has_action_intent"]