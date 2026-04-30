"""
일반 클릭 규칙
"""

from typing import Optional
from . import BaseRule, RuleResult
from ..context.context_rules import (
    CLICK_TRIGGERS,
    extract_click_target,
    build_generic_click_commands
)


class GenericClickRule(BaseRule):
    """일반 클릭 규칙: '버튼 클릭', '텍스트 선택' 등"""
    
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        if not any(kw in text for kw in CLICK_TRIGGERS):
            return None

        target = extract_click_target(text)
        if not target:
            return None
        
        # 복잡한 텍스트는 LLM에게 위임 (더 정확함)
        # - 공백이 있는 경우 (예: "롯데 칠성 음료")
        # - 4글자 이상인 경우
        if " " in target or len(target) > 3:
            return None  # LLM fallback
        
        commands = build_generic_click_commands(target)
        
        return RuleResult(
            matched=True,
            commands=commands,
            response_text=f"'{target}'을 클릭합니다.",
            rule_name="generic_click"
        )
