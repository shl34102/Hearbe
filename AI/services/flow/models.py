"""
플로우 데이터 모델

Pydantic 기반 플로우 관련 데이터 모델 정의
담당: 김재환
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class FlowState(str, Enum):
    """플로우 상태"""
    IDLE = "idle"
    STARTED = "started"
    STEP_EXECUTING = "step_executing"
    WAITING_USER = "waiting_user"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    COMPLETED = "completed"
    ABORTED = "aborted"


class FlowType(str, Enum):
    """플로우 타입"""
    SEARCH = "search"
    CHECKOUT = "checkout"
    SIGNUP = "signup"


class Intent(str, Enum):
    """사용자 의도 타입"""
    SEARCH = "search"
    ADD_TO_CART = "add_to_cart"
    CHECKOUT = "checkout"
    SIGNUP = "signup"
    NAVIGATE = "navigate"
    COMPARE = "compare"
    INQUIRY = "inquiry"
    UNKNOWN = "unknown"


class ToolCall(BaseModel):
    """MCP 도구 호출"""
    tool_name: str = Field(..., description="도구 이름")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="도구 인자")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "navigate_to_url",
                "arguments": {"url": "https://www.coupang.com"}
            }
        }


class ValidationConfig(BaseModel):
    """단계 검증 설정"""
    type: str = Field(..., description="검증 타입 (selector_exists, url_contains 등)")
    selector: Optional[str] = Field(None, description="CSS 선택자 (selector_exists용)")
    value: Optional[str] = Field(None, description="비교 값 (url_contains용)")


class FlowStep(BaseModel):
    """플로우 단계"""
    step_id: int = Field(..., description="단계 ID")
    name: str = Field(..., description="단계 이름")
    prompt: str = Field(..., description="TTS 안내 문구")
    action: Optional[ToolCall] = Field(None, description="MCP 명령")
    required_fields: List[str] = Field(default_factory=list, description="필수 입력 필드")
    user_confirmation: bool = Field(False, description="사용자 확인 필요 여부")
    validation: Optional[ValidationConfig] = Field(None, description="성공 검증 설정")
    fallback: str = Field("", description="실패 시 안내 문구")
    next_step: Optional[int] = Field(None, description="다음 단계 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "step_id": 1,
                "name": "navigate_to_site",
                "prompt": "쿠팡에 접속합니다.",
                "action": {
                    "tool_name": "navigate_to_url",
                    "arguments": {"url": "https://www.coupang.com"}
                },
                "validation": {
                    "type": "url_contains",
                    "value": "coupang.com"
                },
                "next_step": 2
            }
        }


class FlowDefinition(BaseModel):
    """플로우 정의"""
    flow_id: str = Field(..., description="플로우 ID")
    flow_type: FlowType = Field(..., description="플로우 타입")
    site: str = Field(..., description="대상 사이트")
    total_steps: int = Field(..., description="총 단계 수")
    steps: List[FlowStep] = Field(..., description="단계 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "flow_id": "coupang_search",
                "flow_type": "search",
                "site": "coupang",
                "total_steps": 4,
                "steps": []
            }
        }


class FlowContext(BaseModel):
    """플로우 실행 컨텍스트"""
    session_id: str = Field(..., description="세션 ID")
    flow_id: str = Field(..., description="플로우 ID")
    current_step_index: int = Field(0, description="현재 단계 인덱스")
    state: FlowState = Field(FlowState.IDLE, description="플로우 상태")
    collected_data: Dict[str, Any] = Field(default_factory=dict, description="수집된 데이터")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    retry_count: int = Field(0, description="재시도 횟수")


class StepResult(BaseModel):
    """단계 실행 결과"""
    success: bool = Field(..., description="성공 여부")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="실행할 MCP 명령")
    prompt: str = Field("", description="TTS 안내 메시지")
    requires_input: bool = Field(False, description="사용자 입력 필요 여부")
    error: Optional[str] = Field(None, description="에러 메시지")


class IntentResult(BaseModel):
    """의도 분석 결과"""
    intent: Intent = Field(..., description="분석된 의도")
    site: Optional[str] = Field(None, description="대상 사이트")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="추출된 파라미터")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="신뢰도")
    requires_flow: bool = Field(False, description="플로우 엔진 필요 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "intent": "search",
                "site": "coupang",
                "parameters": {"keyword": "물티슈"},
                "confidence": 0.95,
                "requires_flow": False
            }
        }


# WebSocket 메시지 모델
class ToolCallMessage(BaseModel):
    """MCP 도구 호출 요청 메시지"""
    type: str = Field("tool_call", const=True)
    request_id: str = Field(..., description="요청 ID")
    tool_calls: List[ToolCall] = Field(..., description="도구 호출 목록")


class FlowStepMessage(BaseModel):
    """플로우 단계 진행 메시지"""
    type: str = Field("flow_step", const=True)
    flow_id: str = Field(..., description="플로우 ID")
    current_step: int = Field(..., description="현재 단계")
    total_steps: int = Field(..., description="총 단계 수")
    prompt: str = Field(..., description="안내 문구")
    requires_input: bool = Field(False, description="사용자 입력 필요 여부")


class MCPResultMessage(BaseModel):
    """MCP 실행 결과 메시지"""
    type: str = Field("mcp_result", const=True)
    request_id: str = Field(..., description="요청 ID")
    success: bool = Field(..., description="성공 여부")
    result: Optional[Dict[str, Any]] = Field(None, description="결과 데이터")
    error: Optional[str] = Field(None, description="에러 메시지")
