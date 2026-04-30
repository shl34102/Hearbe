"""
LLM Planner 서비스

규칙 기반 CommandGenerator + LLM fallback 통합
"""

import logging
import os
from typing import Optional, List, Dict, Any

from core.interfaces import (
    ILLMPlanner, IntentResult, SessionState,
    LLMResponse, MCPCommand
)

from ..generators.command_generator import CommandGenerator, CommandResult
from ..generators.llm_generator import LLMGenerator, LLMResult, resolve_llm_api_key
from ..generators.tts_text_generator import TTSTextGenerator
from ..sites.site_manager import get_page_type
from .routing import LLMRoutingPolicy
from .selection import select_from_results
from services.llm.rules.product_option import handle_product_option_rule
from .cart_action import handle_cart_action
from .order_list_action import handle_order_list_action
from .hearbe_order_history_action import handle_hearbe_order_history_action
from .product_info_action import handle_product_info_action
from .search_cheapest_action import handle_search_cheapest_action
from .fallback import build_llm_fallback_response

logger = logging.getLogger(__name__)


class LLMPlanner(ILLMPlanner):
    """
    LLM Planner 서비스

    1. 규칙 기반 CommandGenerator로 먼저 시도
    2. 매칭 실패 시 LLMGenerator로 fallback
    """

    def __init__(self, use_llm_fallback: bool = True):
        self._rule_generator: Optional[CommandGenerator] = None
        self._llm_generator: Optional[LLMGenerator] = None
        self._tts_text_generator: Optional[TTSTextGenerator] = None
        self._use_llm_fallback = use_llm_fallback
        self._routing_policy = LLMRoutingPolicy()
        self._use_llm_tts = os.getenv("LLM_TTS_SEPARATE", "true").lower() in ("1", "true", "yes", "y")

    async def initialize(self):
        """초기화"""
        self._rule_generator = CommandGenerator()
        
        # LLM fallback 활성화 시
        if self._use_llm_fallback:
            api_key = resolve_llm_api_key()
            if api_key:
                self._llm_generator = LLMGenerator(api_key=api_key)
                if self._use_llm_tts:
                    self._tts_text_generator = TTSTextGenerator(api_key=api_key)
                logger.info("LLMPlanner initialized with LLM fallback")
            else:
                logger.warning(
                    "No LLM API key set (LLM_API_KEY_NAME or GMS_API_KEY/OPENAI_API_KEY), "
                    "LLM fallback disabled"
                )
                self._use_llm_fallback = False
        else:
            logger.info("LLMPlanner initialized (rule-based only)")

    async def generate_commands(
        self,
        user_text: str,
        intent: IntentResult,
        session: SessionState
    ) -> LLMResponse:
        """
        사용자 발화를 MCP 명령으로 변환

        Args:
            user_text: 사용자 발화 텍스트
            intent: 의도 분석 결과
            session: 현재 세션 상태

        Returns:
            LLMResponse: 생성된 명령 및 응답
        """
        if not self._rule_generator:
            self._rule_generator = CommandGenerator()

        current_url = session.current_url if session else ""
        conversation_history = session.conversation_history if session else None
        session_context = session.context if session else None

        # Some pages have "page-scoped" actions that must take priority over generic
        # selection (e.g., "N번째 주문 상세보기" on order list pages). Otherwise,
        # a stale search selection can steal the intent and drift to a product page.
        current_page_type = get_page_type(current_url) if current_url else None
        if current_page_type == "orderlist":
            order_list_action = handle_order_list_action(user_text, session)
            if order_list_action:
                return order_list_action

        # 1. Selection from recent search results (prefer session-aware match)
        selection = select_from_results(user_text, session)
        if selection:
            return selection

        # 1.05. Option selection on product detail (avoid LLM click_text on recommendation items)
        option_selection = handle_product_option_rule(user_text, session)
        if option_selection:
            return option_selection

        # 1.06. Page-scoped actions should win over generic rules/LLM fallback.
        # These handlers are safe because they gate on current_url/page_type internally.
        if current_page_type != "orderlist":
            order_list_action = handle_order_list_action(user_text, session)
            if order_list_action:
                return order_list_action

        # 1.1. Rule-based pass
        rule_result = await self._rule_generator.generate_rules(user_text, current_url)

        # 1.5. Post-rule session-aware handlers
        if rule_result.matched_rule == "none":
            search_cheapest_action = handle_search_cheapest_action(user_text, session)
            if search_cheapest_action:
                return search_cheapest_action
            hearbe_order_history_action = handle_hearbe_order_history_action(user_text, session)
            if hearbe_order_history_action:
                return hearbe_order_history_action
            cart_action = handle_cart_action(user_text, session)
            if cart_action:
                return cart_action
            product_info_action = handle_product_info_action(user_text, session)
            if product_info_action:
                return product_info_action
        decision = self._routing_policy.decide(user_text, intent, rule_result)

        # 2. LLM fallback by policy
        if decision.use_llm:
            if self._use_llm_fallback and self._llm_generator:
                logger.info(
                    f"LLM routing: rule={rule_result.matched_rule}, reason={decision.reason}, text='{user_text}'"
                )
                llm_result = await self._llm_generator.generate(
                    user_text=user_text,
                    current_url=current_url,
                    conversation_history=conversation_history,
                    session_context=session_context
                )

                if llm_result.success and llm_result.commands:
                    response_text = llm_result.response_text
                    if self._tts_text_generator:
                        page_type = get_page_type(current_url) if current_url else None
                        response_text = await self._tts_text_generator.generate(
                            user_text=user_text,
                            current_url=current_url,
                            page_type=page_type,
                            commands=llm_result.commands,
                            fallback_text=llm_result.response_text,
                            session_context=session_context,
                        )
                    return self._llm_result_to_response(llm_result, response_text)
                if llm_result.success:
                    fallback = build_llm_fallback_response(
                        user_text=user_text,
                        response_text=llm_result.response_text
                    )
                    if fallback:
                        return fallback
                logger.info(
                    "LLM fallback returned no commands (success=%s, error=%s); using rule result",
                    llm_result.success,
                    llm_result.error
                )
        return self._to_response(rule_result)

    def _to_response(self, result: CommandResult) -> LLMResponse:
        """CommandResult → LLMResponse 변환"""
        commands = [
            MCPCommand(
                tool_name=cmd.tool_name,
                arguments=cmd.arguments,
                description=cmd.description
            )
            for cmd in result.commands
        ]

        return LLMResponse(
            text=result.response_text,
            commands=commands,
            requires_flow=result.requires_flow,
            flow_type=result.flow_type
        )

    def _llm_result_to_response(self, result: LLMResult, response_text: Optional[str] = None) -> LLMResponse:
        """LLMResult → LLMResponse 변환"""
        commands = [
            MCPCommand(
                tool_name=cmd.tool_name,
                arguments=cmd.arguments,
                description=cmd.description
            )
            for cmd in result.commands
        ]

        return LLMResponse(
            text=response_text if response_text is not None else result.response_text,
            commands=commands,
            requires_flow=False,
            flow_type=None
        )

    async def generate_response(self, context: Dict[str, Any]) -> str:
        """
        사용자에게 전달할 응답 텍스트 생성

        Args:
            context: 현재 컨텍스트 (검색 결과, 상품 정보 등)

        Returns:
            str: 응답 텍스트
        """
        # MCP 결과 기반 응답 생성
        mcp_result = context.get("mcp_result", {})
        if mcp_result.get("success"):
            return "작업이 완료되었습니다."
        elif mcp_result.get("error"):
            return f"작업 중 오류가 발생했습니다: {mcp_result.get('error')}"
        return "알겠습니다."

    async def should_delegate_to_flow(self, intent: Optional[IntentResult]) -> Optional[str]:
        """
        Flow Engine 위임 여부 판단

        Args:
            intent: 의도 분석 결과

        Returns:
            str: 위임할 플로우 타입 (signup, checkout) 또는 None
        """
        if not intent:
            return None
        
        from core.interfaces import IntentType
        
        flow_mapping = {
            IntentType.CHECKOUT: "checkout",
            IntentType.SIGNUP: "signup",
        }
        
        return flow_mapping.get(intent.intent)

    async def shutdown(self):
        """리소스 정리"""
        self._rule_generator = None
        self._llm_generator = None
        self._tts_text_generator = None
        logger.info("LLMPlanner shutdown")
