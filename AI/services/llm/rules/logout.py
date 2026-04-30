# -*- coding: utf-8 -*-
"""Logout rule."""

import re
from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import build_click_command, build_click_text_command
from ..sites.site_manager import get_page_type, get_selector


class LogoutRule(BaseRule):
    """Logout rule: click the logout button only."""

    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not _is_logout_intent(text):
            return None

        selector = None
        if current_url:
            selector = get_selector(current_url, "logout")

        page_type = get_page_type(current_url) if current_url else None
        if not selector and current_site and page_type:
            selector = current_site.get_selector(page_type, "logout")
            if not selector:
                selector = current_site.get_selector(page_type, "nav_logout")

        commands = []
        if selector:
            commands.append(build_click_command(selector, "Click logout button"))
        else:
            commands.append(build_click_text_command("\ub85c\uadf8\uc544\uc6c3", "Click logout button"))

        response_text = "\ub85c\uadf8\uc544\uc6c3 \ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?" if _needs_logout_confirm(current_url, current_site) else "\ub85c\uadf8\uc544\uc6c3 \ub418\uc5c8\uc2b5\ub2c8\ub2e4."

        return RuleResult(
            matched=True,
            commands=commands,
            response_text=response_text,
            rule_name="logout",
        )


def _is_logout_intent(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "logout" in lowered:
        return True
    if "\ub85c\uadf8\uc544\uc6c3" in text:
        return True
    return False


def _needs_logout_confirm(current_url: str, current_site) -> bool:
    if not current_url:
        return False
    if current_site and getattr(current_site, "site_id", "") != "hearbe":
        return False
    lowered = current_url.lower()
    return bool(re.search(r"/c/mall(?:\\b|/|\\?)", lowered))


__all__ = ["LogoutRule"]
