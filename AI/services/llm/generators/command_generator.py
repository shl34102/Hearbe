"""
자연어 → MCP 명령 변환기 (리팩토링 버전)

규칙 기반 매칭 + LLM fallback으로 명령을 생성합니다.
실제 규칙 로직은 rules 모듈에 분리되어 있습니다.
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from ..sites.site_manager import get_site_manager, get_current_site
from ..context.context_rules import GeneratedCommand
from ..rules import BaseRule
from ..rules.site_access import SiteAccessRule
from ..rules.select import SearchSelectRule
from ..rules.search import SearchRule
from ..rules.search_sort import SearchSortRule
from ..rules.orderdetail import OrderDetailRule
from ..rules.cart import CartRule
from ..rules.login import LoginRule
from ..rules.order_list import OrderListRule
from ..rules.hearbe_nav import HearbeNavRule
from ..rules.hearbe_mall_select import HearbeMallSelectRule
from ..rules.hearbe_main_mode import HearbeMainModeRule
from ..rules.hearbe_signup import HearbeSignupRule
from ..rules.checkout import CheckoutRule
from ..rules.logout import LogoutRule
from ..rules.generic import GenericClickRule

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """명령 생성 결과"""
    commands: list[GeneratedCommand] = field(default_factory=list)
    response_text: str = ""
    matched_rule: str = "none"
    requires_flow: bool = False
    flow_type: str = ""


class CommandGenerator:
    """
    자연어 → MCP 명령 변환기
    
    규칙 모듈을 조합하여 명령을 생성하고,
    실패 시 LLM fallback을 사용합니다.
    """
    
    def __init__(self):
        self.site_manager = get_site_manager()
        self.llm_generator = None  # lazy init
        
        # 규칙 인스턴스 생성
        self.rules: list[BaseRule] = [
            SiteAccessRule(self.site_manager),
            HearbeNavRule(self.site_manager),
            HearbeMallSelectRule(self.site_manager),
            HearbeMainModeRule(self.site_manager),
            HearbeSignupRule(self.site_manager),
            SearchSelectRule(self.site_manager),
            SearchRule(self.site_manager),
            SearchSortRule(self.site_manager),
            OrderDetailRule(self.site_manager),
            CartRule(self.site_manager),
            OrderListRule(self.site_manager),
            LogoutRule(self.site_manager),
            LoginRule(self.site_manager),
            CheckoutRule(self.site_manager),
            GenericClickRule(self.site_manager),
        ]
    
    async def generate_rules(self, user_text: str, current_url: str = "") -> CommandResult:
        """
        지역 기반만 사용하여 명령 생성
        
        Args:
            user_text: 사용자 입력 텍스트
            current_url: 현재 브라우저 URL
            
        Returns:
            CommandResult: 그룹 기반 결과 (매칭 실패시 matched_rule="none")
        """
        text = user_text.strip()
        if not text:
            return CommandResult(
                commands=[],
                response_text="명령을 입력해주세요.",
                matched_rule="empty"
            )
        
        current_site = get_current_site(current_url)
        
        # 그룹 순서로 체크
        for rule in self.rules:
            result = rule.check(text, current_url, current_site)
            if result and result.matched:
                return CommandResult(
                    commands=result.commands,
                    response_text=result.response_text,
                    matched_rule=result.rule_name
                )
        
        return CommandResult(
            commands=[],
            response_text=f"'{text}' 명령을 어떤 방법으로 처리할지 모르겠습니다.",
            matched_rule="none"
        )

    async def generate(self, user_text: str, current_url: str = "") -> CommandResult:
        """
        자연어를 MCP 명령으로 변환 (LLM fallback 포함)
        
        Args:
            user_text: 사용자 입력 텍스트
            current_url: 현재 브라우저 URL
            
        Returns:
            CommandResult: 생성된 명령 및 응답
        """
        result = await self.generate_rules(user_text, current_url)
        if result.matched_rule != "none":
            return result

        current_site = get_current_site(current_url)
        return await self._try_llm_fallback(user_text.strip(), current_url, current_site)

    async def _call_llm_with_context(
        self, 
        user_text: str, 
        current_url: str,
        current_site
    ) -> CommandResult:
        """
        LLM 호출 (공통 로직)
        
        Args:
            user_text: 사용자 입력 (실패 컨텍스트 포함 가능)
            current_url: 현재 URL
            current_site: 현재 사이트
            
        Returns:
            CommandResult
        """
        from .llm_generator import resolve_llm_api_key

        # API key availability check (configurable)
        if not resolve_llm_api_key():
            return CommandResult(
                commands=[],
                response_text=f"'{user_text}' 명령을 어떻게 처리할지 모르겠습니다.",
                matched_rule="none"
            )
        
        # lazy init llm_generator
        if self.llm_generator is None:
            from .llm_generator import LLMGenerator
            self.llm_generator = LLMGenerator()
        
        # 페이지 컨텍스트 구성
        from ..sites.site_manager import get_page_type
        page_type = get_page_type(current_url) if current_url else None
        
        # 사용 가능한 셀렉터 정보 수집
        available_selectors = {}
        if current_site and page_type:
            page_selectors = current_site.get_page_selectors(page_type)
            if page_selectors:
                available_selectors = page_selectors.selectors
        if current_url and "login.coupang.com/login/pincode" in current_url:
            available_selectors = _filter_pincode_selectors(available_selectors)
        
        # LLM에게 위임
        try:
            result = await self.llm_generator.generate(
                user_text=user_text,
                current_url=current_url,
                page_type=page_type,
                available_selectors=available_selectors
            )
            
            # LLMResult → CommandResult 변환
            return CommandResult(
                commands=result.commands,
                response_text=result.response_text,
                matched_rule="llm_fallback" if result.success else "llm_error"
            )
        except Exception as e:
            import traceback
            logger.error(f"LLM 생성 실패: {e}")
            logger.error(traceback.format_exc())
            return CommandResult(
                commands=[],
                response_text=f"'{user_text}' 명령 처리 중 오류가 발생했습니다.",
                matched_rule="llm_error"
            )
    
    async def _try_llm_fallback(self, user_text: str, current_url: str, current_site) -> CommandResult:
        """LLM으로 명령 생성 시도 (규칙 실패 시)"""
        return await self._call_llm_with_context(user_text, current_url, current_site)
    
    async def retry_with_llm(
        self, 
        original_text: str, 
        current_url: str,
        failed_command: Optional[GeneratedCommand] = None,
        error_message: Optional[str] = None
    ) -> CommandResult:
        """
        실행 실패 시 LLM으로 재시도
        
        Args:
            original_text: 원래 사용자 입력
            current_url: 현재 URL
            failed_command: 실패한 명령 (선택)
            error_message: 실패 에러 메시지 (선택)
            
        Returns:
            CommandResult: 재시도 명령
        """
        # 실패 컨텍스트를 포함한 프롬프트 구성
        enhanced_text = original_text
        if failed_command and error_message:
            enhanced_text = (
                f"{original_text}\n\n"
                f"[이전 시도 실패]\n"
                f"명령: {failed_command.tool_name}({failed_command.arguments})\n"
                f"오류: {error_message}\n\n"
                f"다른 방법을 시도해주세요."
            )
        
        current_site = get_current_site(current_url)
        result = await self._call_llm_with_context(enhanced_text, current_url, current_site)
        
        # matched_rule 수정 (재시도임을 표시)
        if result.matched_rule == "llm_fallback":
            result.matched_rule = "llm_retry"
            result.response_text = f"재시도: {result.response_text}"
        
        return result


def _filter_pincode_selectors(selectors: dict) -> dict:
    if not selectors:
        return selectors
    allow_keys = {
        "pincode_method_sms",
        "pincode_method_email",
        "pincode_method_submit",
        "pincode_input",
        "pincode_submit",
    }
    filtered = {k: v for k, v in selectors.items() if k in allow_keys}
    return filtered or selectors
