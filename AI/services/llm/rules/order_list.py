# -*- coding: utf-8 -*-
"""Order list rule."""

from typing import Optional

from . import BaseRule, RuleResult
from ..context.context_rules import GeneratedCommand
from ..sites.site_manager import get_page_type, get_current_site

# Order list / history triggers.
ORDER_LIST_TRIGGERS = (
    "\uc8fc\ubb38 \ubaa9\ub85d",
    "\uc8fc\ubb38\ubaa9\ub85d",
    "\uc8fc\ubb38 \ub0b4\uc5ed",
    "\uc8fc\ubb38\ub0b4\uc5ed",
    "\uc8fc\ubb38 \uc870\ud68c",
    "\uc8fc\ubb38\uc870\ud68c",
    "\uc8fc\ubb38 \ub9ac\uc2a4\ud2b8",
    "\uc8fc\ubb38\ub9ac\uc2a4\ud2b8",
    "\ub9c8\uc774\ud398\uc774\uc9c0",
    "\ub9c8\uc774 \ud398\uc774\uc9c0",
    "\ub9c8\uc774\ucfe0\ud321",
    "\ub9c8\uc774 \ucfe0\ud321",
)

MSG_ALREADY_ON_ORDER_LIST = "\uc774\ubbf8 \uc8fc\ubb38 \ubaa9\ub85d \ud398\uc774\uc9c0\uc5d0 \uc788\uc5b4\uc694."
MSG_GO_TO_ORDER_LIST = "\uc8fc\ubb38 \ubaa9\ub85d\uc73c\ub85c \uc774\ub3d9\ud569\ub2c8\ub2e4."


class OrderListRule(BaseRule):
    """Order list rule: navigate to the order history/list page."""

    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not _is_coupang_site(current_url, current_site):
            return None
        if not any(kw in text for kw in ORDER_LIST_TRIGGERS):
            return None

        page_type = get_page_type(current_url) if current_url else None
        if page_type == "orderlist":
            # Let order list action handler decide how to respond on the list page.
            return None

        commands: list[GeneratedCommand] = []
        order_list_url = None
        if current_site:
            order_list_url = current_site.get_url("mypage")

        if order_list_url:
            commands.append(
                GeneratedCommand(
                    tool_name="goto",
                    arguments={"url": order_list_url},
                    description="Go to order list",
                )
            )
            commands.append(
                GeneratedCommand(
                    tool_name="wait",
                    arguments={"ms": 2500},
                    description="Wait for order list page to load",
                )
            )
            commands.append(
                GeneratedCommand(
                    tool_name="extract_order_list",
                    arguments={},
                    description="Extract order list",
                )
            )
        else:
            commands.append(
                GeneratedCommand(
                    tool_name="click_text",
                    arguments={"text": "\ub9c8\uc774\ucfe0\ud321"},
                    description="Click My Coupang link",
                )
            )
            commands.append(
                GeneratedCommand(
                    tool_name="wait_for_new_page",
                    arguments={"timeout_ms": 3000, "focus": True},
                    description="Wait for order list page",
                )
            )
            commands.append(
                GeneratedCommand(
                    tool_name="wait",
                    arguments={"ms": 2500},
                    description="Wait for order list page to load",
                )
            )
            commands.append(
                GeneratedCommand(
                    tool_name="extract_order_list",
                    arguments={},
                    description="Extract order list",
                )
            )

        return RuleResult(
            matched=True,
            commands=commands,
            response_text=MSG_GO_TO_ORDER_LIST,
            rule_name="order_list",
        )


def _is_coupang_site(current_url: str, current_site) -> bool:
    if current_site and getattr(current_site, "site_id", "") == "coupang":
        return True
    site = get_current_site(current_url) if current_url else None
    return bool(site and getattr(site, "site_id", "") == "coupang")
