"""
Flow Engine 서비스 구현

사이트별 회원가입, 결제 플로우 단계별 진행
"""

import logging
from typing import Dict, Any, List, Optional
from core.interfaces import IFlowEngine, FlowStep, FlowDefinition, SessionState
from core.config import get_config

logger = logging.getLogger(__name__)


# 사이트별 플로우 정의
FLOW_DEFINITIONS: Dict[str, Dict[str, FlowDefinition]] = {
    "coupang": {
        "signup": FlowDefinition(
            flow_type="signup",
            site="coupang",
            steps=[
                FlowStep(
                    step_id="email",
                    prompt="회원가입을 시작합니다. 이메일 주소를 말씀해 주세요.",
                    required_fields=["email"],
                    action="input_email",
                    validation="email_format",
                    fallback="올바른 이메일 형식이 아닙니다. 다시 말씀해 주세요."
                ),
                FlowStep(
                    step_id="password",
                    prompt="비밀번호를 입력해 주세요. 비밀번호는 로컬에서 직접 입력합니다.",
                    required_fields=["password"],
                    action="local_input_password",
                    validation="password_strength"
                ),
                FlowStep(
                    step_id="name",
                    prompt="이름을 말씀해 주세요.",
                    required_fields=["name"],
                    action="input_name"
                ),
                FlowStep(
                    step_id="phone",
                    prompt="휴대폰 번호를 말씀해 주세요.",
                    required_fields=["phone"],
                    action="input_phone",
                    validation="phone_format"
                ),
                FlowStep(
                    step_id="verify",
                    prompt="인증번호를 전송했습니다. 인증번호를 말씀해 주세요.",
                    required_fields=["verify_code"],
                    action="input_verify_code"
                ),
                FlowStep(
                    step_id="complete",
                    prompt="회원가입이 완료되었습니다.",
                    action="complete"
                )
            ]
        ),
        "checkout": FlowDefinition(
            flow_type="checkout",
            site="coupang",
            steps=[
                FlowStep(
                    step_id="confirm_cart",
                    prompt="장바구니에 담긴 상품을 확인합니다. {cart_summary} 결제를 진행하시겠습니까?",
                    required_fields=["confirm"],
                    action="get_cart_info"
                ),
                FlowStep(
                    step_id="select_address",
                    prompt="배송지를 선택해 주세요. 기본 배송지는 {default_address}입니다. 이 주소로 배송할까요?",
                    required_fields=["address_confirm"],
                    action="select_address"
                ),
                FlowStep(
                    step_id="select_payment",
                    prompt="결제 수단을 선택해 주세요. 등록된 카드: {cards}. 어떤 카드로 결제하시겠습니까?",
                    required_fields=["payment_method"],
                    action="select_payment"
                ),
                FlowStep(
                    step_id="final_confirm",
                    prompt="최종 결제 금액은 {total_price}원입니다. 결제를 진행하시겠습니까?",
                    required_fields=["final_confirm"],
                    action="final_confirm"
                ),
                FlowStep(
                    step_id="payment_auth",
                    prompt="결제 인증을 진행합니다. 카드 비밀번호를 입력해 주세요.",
                    required_fields=["card_password"],
                    action="local_input_card_password"
                ),
                FlowStep(
                    step_id="complete",
                    prompt="결제가 완료되었습니다.",
                    action="complete"
                )
            ]
        )
    },
    "naver": {
        "signup": FlowDefinition(
            flow_type="signup",
            site="naver",
            steps=[
                FlowStep(
                    step_id="start",
                    prompt="네이버 회원가입을 시작합니다.",
                    action="navigate_signup"
                ),
                # TODO: 네이버 회원가입 플로우 정의
            ]
        ),
        "checkout": FlowDefinition(
            flow_type="checkout",
            site="naver",
            steps=[
                FlowStep(
                    step_id="start",
                    prompt="네이버페이 결제를 시작합니다.",
                    action="navigate_checkout"
                ),
                # TODO: 네이버 결제 플로우 정의
            ]
        )
    },
    "11st": {
        "signup": FlowDefinition(
            flow_type="signup",
            site="11st",
            steps=[]
        ),
        "checkout": FlowDefinition(
            flow_type="checkout",
            site="11st",
            steps=[]
        )
    }
}


class FlowEngine(IFlowEngine):
    """
    쇼핑 플로우 엔진

    Features:
    - 사이트별 회원가입/결제 플로우 관리
    - 단계별 TTS 안내
    - 결제 안전 확인 (Policy/Guard)
    """

    def __init__(self):
        self._config = get_config().flow_engine
        self._active_flows: Dict[str, Dict[str, Any]] = {}  # session_id -> flow state

    async def initialize(self):
        """플로우 엔진 초기화"""
        logger.info("Flow Engine initialized")

    async def start_flow(
        self,
        flow_type: str,
        site: str,
        session: SessionState
    ) -> FlowStep:
        """
        플로우 시작

        Args:
            flow_type: 플로우 타입 (signup, checkout)
            site: 쇼핑몰 사이트
            session: 세션 상태

        Returns:
            FlowStep: 첫 번째 단계
        """
        # 플로우 정의 가져오기
        site_flows = FLOW_DEFINITIONS.get(site, {})
        flow_def = site_flows.get(flow_type)

        if not flow_def or not flow_def.steps:
            raise ValueError(f"Flow not found: {site}/{flow_type}")

        # 플로우 상태 저장
        self._active_flows[session.session_id] = {
            "flow_type": flow_type,
            "site": site,
            "current_step": 0,
            "flow_def": flow_def,
            "user_inputs": {}
        }

        first_step = flow_def.steps[0]
        logger.info(f"Flow started: {site}/{flow_type}, first step: {first_step.step_id}")

        return first_step

    async def next_step(
        self,
        session: SessionState,
        user_input: Dict[str, Any] = None
    ) -> FlowStep:
        """
        다음 단계로 진행

        Args:
            session: 세션 상태
            user_input: 사용자 입력 데이터

        Returns:
            FlowStep: 다음 단계
        """
        flow_state = self._active_flows.get(session.session_id)
        if not flow_state:
            raise ValueError("No active flow for this session")

        flow_def: FlowDefinition = flow_state["flow_def"]
        current_idx = flow_state["current_step"]

        # 현재 단계 유효성 검증
        if user_input:
            current_step = flow_def.steps[current_idx]
            is_valid = await self.validate_step(current_step, user_input)
            if not is_valid:
                # 유효하지 않으면 현재 단계 유지 (fallback 메시지 포함)
                return current_step

            # 입력 저장
            flow_state["user_inputs"].update(user_input)

        # 다음 단계로 이동
        next_idx = current_idx + 1
        if next_idx >= len(flow_def.steps):
            # 플로우 완료
            await self._complete_flow(session)
            return flow_def.steps[-1]  # 마지막 단계 (complete)

        flow_state["current_step"] = next_idx
        next_step = flow_def.steps[next_idx]

        logger.info(f"Flow progressed to step: {next_step.step_id}")
        return next_step

    async def cancel_flow(self, session: SessionState) -> None:
        """
        플로우 취소

        Args:
            session: 세션 상태
        """
        if session.session_id in self._active_flows:
            del self._active_flows[session.session_id]
            logger.info(f"Flow cancelled for session: {session.session_id}")

    def get_available_flows(self, site: str) -> List[str]:
        """
        특정 사이트에서 사용 가능한 플로우 목록

        Args:
            site: 쇼핑몰 사이트

        Returns:
            List[str]: 플로우 타입 목록
        """
        site_flows = FLOW_DEFINITIONS.get(site, {})
        return [
            flow_type for flow_type, flow_def in site_flows.items()
            if flow_def.steps  # 빈 플로우 제외
        ]

    async def validate_step(
        self,
        step: FlowStep,
        user_input: Dict[str, Any]
    ) -> bool:
        """
        단계 유효성 검증

        Args:
            step: 현재 단계
            user_input: 사용자 입력

        Returns:
            bool: 유효 여부
        """
        # 필수 필드 확인
        for field in step.required_fields:
            if field not in user_input or not user_input[field]:
                logger.warning(f"Missing required field: {field}")
                return False

        # 유효성 검사 (validation 필드에 따라)
        validation = step.validation
        if validation == "email_format":
            email = user_input.get("email", "")
            if "@" not in email or "." not in email:
                return False
        elif validation == "phone_format":
            phone = user_input.get("phone", "")
            if not phone.replace("-", "").isdigit() or len(phone.replace("-", "")) < 10:
                return False
        elif validation == "password_strength":
            # 비밀번호는 로컬에서 처리하므로 항상 통과
            pass

        return True

    async def _complete_flow(self, session: SessionState) -> None:
        """플로우 완료 처리"""
        flow_state = self._active_flows.get(session.session_id)
        if flow_state:
            flow_type = flow_state["flow_type"]
            site = flow_state["site"]
            logger.info(f"Flow completed: {site}/{flow_type}")
            del self._active_flows[session.session_id]

    def get_current_step(self, session_id: str) -> Optional[FlowStep]:
        """현재 단계 조회"""
        flow_state = self._active_flows.get(session_id)
        if not flow_state:
            return None

        flow_def: FlowDefinition = flow_state["flow_def"]
        current_idx = flow_state["current_step"]
        return flow_def.steps[current_idx]

    def is_flow_active(self, session_id: str) -> bool:
        """플로우 진행 중 여부"""
        return session_id in self._active_flows

    async def shutdown(self):
        """리소스 정리"""
        self._active_flows.clear()
        logger.info("Flow Engine shutdown")
