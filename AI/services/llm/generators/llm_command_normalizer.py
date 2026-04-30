# -*- coding: utf-8 -*-
"""
Command normalizer for LLM output.
"""

from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse, urlunparse

from ..sites.site_manager import get_page_type, get_selector


class LLMCommandNormalizer:
    """Normalize LLM actions (login-specific corrections)."""

    def normalize(
        self,
        action: str,
        args: Dict[str, Any],
        current_url: str,
    ) -> Tuple[str, Dict[str, Any]]:
        if not action:
            return action, args

        if action == "goto" and isinstance(args, dict):
            url = args.get("url")
            fixed = self._normalize_login_goto(url)
            if fixed:
                args["url"] = fixed

        if not current_url:
            return action, args

        if get_page_type(current_url) != "login":
            return action, args

        if action not in ("submit_login", "login_submit", "submit"):
            return action, args

        selector = args.get("selector") if isinstance(args, dict) else None
        if not selector:
            selector = (
                get_selector(current_url, "login_button")
                or get_selector(current_url, "submit_button")
                or "button[type='submit']"
            )
        return "click", {"selector": selector}

    def _normalize_login_goto(self, url: Optional[str]) -> Optional[str]:
        if not url or not isinstance(url, str):
            return None
        try:
            parsed = urlparse(url)
        except Exception:
            return None
        host = (parsed.netloc or "").lower()
        if "login.coupang.com" not in host:
            return None
        if parsed.path in ("/login.pang", "/login"):
            new_path = "/login/login.pang"
            return urlunparse(parsed._replace(path=new_path))
        return None
