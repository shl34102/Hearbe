"""
플로우 엔진 서비스

사이트별 쇼핑 플로우(검색, 결제, 회원가입) 단계별 처리
담당: 김재환
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FlowState(Enum):
    """플로우 상태"""
    IDLE = "idle"                       # 대기
    STARTED = "started"                 # 플로우 시작됨
    STEP_EXECUTING = "step_executing"   # 단계 실행 중
    WAITING_USER = "waiting_user"       # 사용자 입력 대기
    STEP_COMPLETED = "step_completed"   # 단계 완료
    STEP_FAILED = "step_failed"         # 단계 실패
    COMPLETED = "completed"             # 플로우 완료
    ABORTED = "aborted"                 # 플로우 중단


class FlowType(Enum):
    """플로우 타입"""
    SEARCH = "search"
    CHECKOUT = "checkout"
    SIGNUP = "signup"


@dataclass
class FlowStep:
    """플로우 단계 정의"""
    step_id: int
    name: str
    prompt: str                             # TTS 안내 문구
    action: Optional[Dict[str, Any]]        # MCP 명령 (없으면 사용자 입력만 대기)
    required_fields: List[str] = field(default_factory=list)
    user_confirmation: bool = False         # 사용자 확인 필요 여부
    validation: Optional[Dict[str, Any]] = None
    fallback: str = ""                      # 실패 시 안내 문구
    next_step: Optional[int] = None


@dataclass
class FlowDefinition:
    """플로우 정의"""
    flow_id: str
    flow_type: FlowType
    site: str
    total_steps: int
    steps: List[FlowStep]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowDefinition":
        """딕셔너리에서 FlowDefinition 생성"""
        steps = [
            FlowStep(
                step_id=s["step_id"],
                name=s["name"],
                prompt=s["prompt"],
                action=s.get("action"),
                required_fields=s.get("required_fields", []),
                user_confirmation=s.get("user_confirmation", False),
                validation=s.get("validation"),
                fallback=s.get("fallback", ""),
                next_step=s.get("next_step")
            )
            for s in data.get("steps", [])
        ]

        return cls(
            flow_id=data["flow_id"],
            flow_type=FlowType(data["flow_type"]),
            site=data["site"],
            total_steps=data.get("total_steps", len(steps)),
            steps=steps
        )


@dataclass
class FlowContext:
    """플로우 실행 컨텍스트"""
    flow_definition: FlowDefinition
    current_step_index: int = 0
    state: FlowState = FlowState.IDLE
    collected_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def current_step(self) -> Optional[FlowStep]:
        """현재 단계 반환"""
        if 0 <= self.current_step_index < len(self.flow_definition.steps):
            return self.flow_definition.steps[self.current_step_index]
        return None

    @property
    def is_completed(self) -> bool:
        """플로우 완료 여부"""
        return self.state == FlowState.COMPLETED

    @property
    def progress(self) -> str:
        """진행률 문자열"""
        return f"{self.current_step_index + 1}/{self.flow_definition.total_steps}"


@dataclass
class StepResult:
    """단계 실행 결과"""
    success: bool
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    prompt: str = ""                # TTS로 안내할 메시지
    requires_input: bool = False    # 사용자 입력 필요 여부
    error: Optional[str] = None


class FlowEngine:
    """
    플로우 엔진

    사이트별 쇼핑 플로우를 단계별로 처리
    """

    def __init__(self, flows_dir: str = None):
        """
        Args:
            flows_dir: 플로우 JSON 파일 디렉토리 경로
        """
        if flows_dir is None:
            # 기본 경로: AI/flows/
            flows_dir = Path(__file__).parent.parent / "flows"

        self._flows_dir = Path(flows_dir)
        self._loaded_flows: Dict[str, FlowDefinition] = {}
        self._active_contexts: Dict[str, FlowContext] = {}  # session_id -> FlowContext

        logger.info(f"FlowEngine initialized with flows_dir: {self._flows_dir}")

    async def initialize(self):
        """플로우 정의 파일 로딩"""
        await self._load_all_flows()
        logger.info(f"Loaded {len(self._loaded_flows)} flow definitions")

    async def _load_all_flows(self):
        """모든 플로우 JSON 파일 로딩"""
        if not self._flows_dir.exists():
            logger.warning(f"Flows directory not found: {self._flows_dir}")
            return

        for site_dir in self._flows_dir.iterdir():
            if site_dir.is_dir():
                for flow_file in site_dir.glob("*.json"):
                    await self._load_flow_file(flow_file)

    async def _load_flow_file(self, file_path: Path):
        """단일 플로우 파일 로딩"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            flow_def = FlowDefinition.from_dict(data)
            self._loaded_flows[flow_def.flow_id] = flow_def
            logger.debug(f"Loaded flow: {flow_def.flow_id}")

        except Exception as e:
            logger.error(f"Failed to load flow file {file_path}: {e}")

    def get_flow(self, flow_id: str) -> Optional[FlowDefinition]:
        """플로우 정의 조회"""
        return self._loaded_flows.get(flow_id)

    def list_flows(self, site: str = None) -> List[str]:
        """사용 가능한 플로우 목록"""
        flows = self._loaded_flows.values()
        if site:
            flows = [f for f in flows if f.site == site]
        return [f.flow_id for f in flows]

    async def start_flow(
        self,
        session_id: str,
        flow_id: str,
        initial_data: Dict[str, Any] = None
    ) -> FlowContext:
        """
        플로우 시작

        Args:
            session_id: 세션 ID
            flow_id: 플로우 ID
            initial_data: 초기 데이터 (상품명, 가격 등)

        Returns:
            FlowContext: 플로우 컨텍스트
        """
        flow_def = self.get_flow(flow_id)
        if not flow_def:
            raise ValueError(f"Flow not found: {flow_id}")

        context = FlowContext(
            flow_definition=flow_def,
            current_step_index=0,
            state=FlowState.STARTED,
            collected_data=initial_data or {}
        )

        self._active_contexts[session_id] = context
        logger.info(f"Started flow {flow_id} for session {session_id}")

        return context

    async def execute_step(self, session_id: str) -> StepResult:
        """
        현재 단계 실행

        Args:
            session_id: 세션 ID

        Returns:
            StepResult: 단계 실행 결과
        """
        context = self._active_contexts.get(session_id)
        if not context:
            return StepResult(success=False, error="No active flow")

        step = context.current_step
        if not step:
            return StepResult(success=False, error="No current step")

        context.state = FlowState.STEP_EXECUTING

        # 프롬프트 템플릿 치환
        prompt = self._render_prompt(step.prompt, context.collected_data)

        # MCP 명령 생성
        tool_calls = []
        if step.action:
            tool_calls.append(step.action)

        # 사용자 입력 필요 여부
        requires_input = step.user_confirmation or len(step.required_fields) > 0

        if requires_input:
            context.state = FlowState.WAITING_USER

        return StepResult(
            success=True,
            tool_calls=tool_calls,
            prompt=prompt,
            requires_input=requires_input
        )

    def _render_prompt(self, template: str, data: Dict[str, Any]) -> str:
        """프롬프트 템플릿 렌더링"""
        try:
            return template.format(**data)
        except KeyError:
            # 치환할 데이터가 없으면 원본 반환
            return template

    async def handle_user_input(
        self,
        session_id: str,
        user_input: str
    ) -> StepResult:
        """
        사용자 입력 처리

        Args:
            session_id: 세션 ID
            user_input: 사용자 입력

        Returns:
            StepResult: 처리 결과
        """
        context = self._active_contexts.get(session_id)
        if not context:
            return StepResult(success=False, error="No active flow")

        step = context.current_step
        if not step:
            return StepResult(success=False, error="No current step")

        # 사용자 확인 처리
        if step.user_confirmation:
            if self._is_positive_response(user_input):
                return await self._advance_to_next_step(context, session_id)
            else:
                # 사용자가 거부한 경우
                context.state = FlowState.ABORTED
                return StepResult(
                    success=False,
                    prompt="알겠습니다. 작업을 취소합니다.",
                    error="User cancelled"
                )

        # 필수 필드 수집
        if step.required_fields:
            # TODO: 더 정교한 필드 매핑 구현
            field_name = step.required_fields[0]
            context.collected_data[field_name] = user_input

        return await self._advance_to_next_step(context, session_id)

    def _is_positive_response(self, user_input: str) -> bool:
        """긍정 응답 여부 확인"""
        positive_words = ["네", "예", "응", "좋아", "확인", "맞아", "진행"]
        return any(word in user_input for word in positive_words)

    async def _advance_to_next_step(
        self,
        context: FlowContext,
        session_id: str
    ) -> StepResult:
        """다음 단계로 진행"""
        step = context.current_step

        # 다음 단계 결정
        if step.next_step is not None:
            # 명시된 다음 단계로 이동
            next_index = None
            for i, s in enumerate(context.flow_definition.steps):
                if s.step_id == step.next_step:
                    next_index = i
                    break

            if next_index is not None:
                context.current_step_index = next_index
            else:
                context.current_step_index += 1
        else:
            # 순차적으로 다음 단계
            context.current_step_index += 1

        # 플로우 완료 확인
        if context.current_step_index >= len(context.flow_definition.steps):
            context.state = FlowState.COMPLETED
            return StepResult(
                success=True,
                prompt="작업이 완료되었습니다."
            )

        # 다음 단계 실행
        context.state = FlowState.STEP_COMPLETED
        return await self.execute_step(session_id)

    async def handle_step_result(
        self,
        session_id: str,
        mcp_result: Dict[str, Any]
    ) -> StepResult:
        """
        MCP 실행 결과 처리

        Args:
            session_id: 세션 ID
            mcp_result: MCP 실행 결과

        Returns:
            StepResult: 처리 결과
        """
        context = self._active_contexts.get(session_id)
        if not context:
            return StepResult(success=False, error="No active flow")

        step = context.current_step
        if not step:
            return StepResult(success=False, error="No current step")

        success = mcp_result.get("success", False)

        if success:
            # 성공 - 다음 단계로
            return await self._advance_to_next_step(context, session_id)
        else:
            # 실패 처리
            context.retry_count += 1

            if context.retry_count >= context.max_retries:
                context.state = FlowState.ABORTED
                return StepResult(
                    success=False,
                    prompt=step.fallback or "작업을 완료할 수 없습니다.",
                    error="Max retries exceeded"
                )

            # 재시도
            context.state = FlowState.STEP_FAILED
            return StepResult(
                success=False,
                prompt=step.fallback or "다시 시도합니다.",
                requires_input=False
            )

    def get_current_prompt(self, session_id: str) -> str:
        """현재 단계의 안내 메시지 반환"""
        context = self._active_contexts.get(session_id)
        if not context or not context.current_step:
            return ""

        return self._render_prompt(
            context.current_step.prompt,
            context.collected_data
        )

    def get_progress(self, session_id: str) -> Optional[str]:
        """플로우 진행률 반환"""
        context = self._active_contexts.get(session_id)
        return context.progress if context else None

    async def abort_flow(self, session_id: str) -> bool:
        """플로우 중단"""
        if session_id in self._active_contexts:
            self._active_contexts[session_id].state = FlowState.ABORTED
            del self._active_contexts[session_id]
            logger.info(f"Aborted flow for session {session_id}")
            return True
        return False

    async def close(self):
        """리소스 정리"""
        self._active_contexts.clear()
        self._loaded_flows.clear()
        logger.info("FlowEngine closed")
