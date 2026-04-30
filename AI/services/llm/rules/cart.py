"""
장바구니 규칙
"""

from typing import Optional
from . import BaseRule, RuleResult
from ..context.context_rules import (
    CART_ADD_TRIGGERS,
    CART_GO_TRIGGERS,
    build_add_to_cart_commands,
    build_go_to_cart_commands
)
from ..context.context_rules import GeneratedCommand
from ..sites.site_manager import get_page_type


class CartRule(BaseRule):
    """장바구니 규칙: '장바구니 담기', '장바구니 이동' 등"""
    
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if "장바구니" not in text:
            return None

        # 장바구니 담기
        if any(kw in text for kw in CART_ADD_TRIGGERS):
            commands = build_add_to_cart_commands(current_site, current_url)
            matched_rule = "add_to_cart" if current_site else "add_to_cart_fallback"
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="장바구니에 담고 있습니다.",
                rule_name=matched_rule
            )

        # 장바구니 이동
        if any(kw in text for kw in CART_GO_TRIGGERS) or text == "장바구니":
            commands = build_go_to_cart_commands(current_site, current_url=current_url)
            matched_rule = "go_to_cart" if current_site else "go_to_cart_fallback"
            return RuleResult(
                matched=True,
                commands=commands,
                response_text="장바구니로 이동합니다.",
                rule_name=matched_rule
            )

        return None
