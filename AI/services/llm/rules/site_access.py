"""
사이트 접속 규칙
"""

from typing import Optional
from . import BaseRule, RuleResult
from ..context.context_rules import (
    SITE_KEYWORDS,
    SITE_ACCESS_TRIGGERS,
    build_site_access_commands
)


class SiteAccessRule(BaseRule):
    """사이트 접속 규칙: '쿠팡 접속', '네이버 열어' 등"""
    
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        for keyword, site_id in SITE_KEYWORDS.items():
            if keyword in text and any(t in text for t in SITE_ACCESS_TRIGGERS):
                site = self.site_manager.get_site(site_id)
                if site:
                    commands = build_site_access_commands(site)
                    return RuleResult(
                        matched=True,
                        commands=commands,
                        response_text=f"{site.name}에 접속합니다.",
                        rule_name="site_access"
                    )
        return None
