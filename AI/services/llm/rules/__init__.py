"""
규칙 기반 명령 생성 모듈

각 규칙은 사용자 입력을 분석하여 MCP 명령으로 변환합니다.
"""

from typing import Optional, List
from dataclasses import dataclass
from ..context.context_rules import GeneratedCommand


@dataclass
class RuleResult:
    """규칙 매칭 결과"""
    matched: bool
    commands: List[GeneratedCommand]
    response_text: str
    rule_name: str


class BaseRule:
    """규칙 베이스 클래스"""
    
    def __init__(self, site_manager):
        self.site_manager = site_manager
    
    def check(self, text: str, current_url: str, current_site) -> Optional[RuleResult]:
        """
        규칙 체크
        
        Args:
            text: 사용자 입력
            current_url: 현재 URL
            current_site: 현재 사이트 (SiteConfig)
            
        Returns:
            RuleResult 또는 None (매칭 실패)
        """
        raise NotImplementedError("Subclass must implement check()")
