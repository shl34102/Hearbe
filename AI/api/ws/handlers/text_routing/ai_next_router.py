# -*- coding: utf-8 -*-
"""
Optional AI_next rule router loader.
"""

import sys
from pathlib import Path


class AiNextRouter:
    def __init__(self):
        self._router = self._try_load_router()

    def _try_load_router(self):
        try:
            repo_root = Path(__file__).resolve().parents[4]
            ai_next_root = repo_root / "AI_next"
            if not ai_next_root.exists():
                return None
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from AI_next.core.decision.router import RuleRouter  # type: ignore
            return RuleRouter()
        except Exception:
            return None

    def route(self, text: str, current_url: str):
        if not self._router:
            return None
        try:
            return self._router.route(text, current_url or "")
        except Exception:
            return None
