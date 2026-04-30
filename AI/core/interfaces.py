"""
모듈 인터페이스 정의

모든 모듈의 추상 인터페이스를 정의하여 느슨한 결합 보장
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# 공통 데이터 클래스
# ============================================================================

class IntentType(Enum):
    """사용자 의도 타입"""
    SEARCH = "search"
    COMPARE = "compare"
    ADD_TO_CART = "add_to_cart"
    CHECKOUT = "checkout"
    SIGNUP = "signup"
    LOGIN = "login"
    SELECT_ITEM = "select_item"
    NAVIGATE = "navigate"
    ASK_INFO = "ask_info"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


@dataclass
class ASRResult:
    """ASR transcription result"""
    text: str
    confidence: float = 1.0
    language: str = "ko"
    duration: float = 0.0
    is_final: bool = True
    segment_id: Optional[str] = None


@dataclass
class IntentResult:
    """의도 분석 결과"""
    intent: IntentType
    confidence: float
    entities: Dict[str, Any] = None
    raw_text: str = ""

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


@dataclass
class NEREntity:
    """개체명 인식 결과"""
    entity_type: str  # product_name, brand, price, quantity, category, etc.
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class MCPCommand:
    """MCP 도구 호출 명령"""
    tool_name: str
    arguments: Dict[str, Any]
    description: str = ""

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = {}


@dataclass
class LLMResponse:
    """LLM 응답"""
    text: str
    commands: List[MCPCommand] = None
    requires_flow: bool = False
    flow_type: Optional[str] = None
    confidence: float = 1.0

    def __post_init__(self):
        if self.commands is None:
            self.commands = []


@dataclass
class TTSChunk:
    """TTS 오디오 청크"""
    audio_data: bytes
    is_final: bool = False
    sample_rate: int = 24000
    format: str = "pcm"


@dataclass
class OCRResult:
    """OCR 결과"""
    text: str
    regions: List[Dict[str, Any]] = None
    confidence: float = 1.0

    def __post_init__(self):
        if self.regions is None:
            self.regions = []


@dataclass
class FlowStep:
    """플로우 단계"""
    step_id: str
    prompt: str  # TTS 안내 문구
    required_fields: List[str] = None
    action: str = ""
    validation: str = ""
    fallback: str = ""

    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []


@dataclass
class FlowDefinition:
    """플로우 정의"""
    flow_type: str  # signup, checkout
    site: str  # coupang, naver, 11st
    steps: List[FlowStep] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


@dataclass
class SessionState:
    """세션 상태"""
    session_id: str
    user_id: Optional[str] = None
    current_site: Optional[str] = None
    current_url: Optional[str] = None  # 현재 브라우저 URL
    current_flow: Optional[str] = None
    flow_step: int = 0
    search_history: List[str] = None
    cart_items: List[Dict[str, Any]] = None
    context: Dict[str, Any] = None
    conversation_history: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.search_history is None:
            self.search_history = []
        if self.cart_items is None:
            self.cart_items = []
        if self.context is None:
            self.context = {}
        if self.conversation_history is None:
            self.conversation_history = []


# ============================================================================
# ASR 모듈 인터페이스
# ============================================================================

class IASRService(ABC):
    """음성 인식 (ASR) 서비스 인터페이스"""

    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> ASRResult:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio data (WAV/PCM)

        Returns:
            ASRResult: Transcription result
        """
        pass

    @abstractmethod
    async def transcribe_stream(self, audio_chunks: AsyncGenerator[bytes, None]) -> AsyncGenerator[ASRResult, None]:
        """
        Stream audio and yield real-time transcription results.

        Args:
            audio_chunks: Async generator of audio chunks

        Yields:
            ASRResult: Intermediate/final transcription results
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """모델 로드 완료 여부"""
        pass


# ============================================================================
# NLU 모듈 인터페이스
# ============================================================================

class INLUService(ABC):
    """자연어 이해 (NLU) 서비스 인터페이스"""

    @abstractmethod
    async def analyze_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """
        사용자 발화에서 의도 분석

        Args:
            text: 사용자 발화 텍스트
            context: 대화 컨텍스트

        Returns:
            IntentResult: 의도 분석 결과
        """
        pass

    @abstractmethod
    async def extract_entities(self, text: str) -> List[NEREntity]:
        """
        개체명 인식 (NER)

        Args:
            text: 분석할 텍스트

        Returns:
            List[NEREntity]: 추출된 개체 목록
        """
        pass

    @abstractmethod
    async def resolve_reference(self, text: str, context: Dict[str, Any]) -> str:
        """
        대명사/참조 해석

        Args:
            text: 원본 텍스트 ("그거", "두 번째 거" 등)
            context: 이전 검색 결과 등의 컨텍스트

        Returns:
            str: 해석된 텍스트
        """
        pass


# ============================================================================
# LLM Planner 모듈 인터페이스
# ============================================================================

class ILLMPlanner(ABC):
    """LLM 기반 명령 생성 인터페이스"""

    @abstractmethod
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
        pass

    @abstractmethod
    async def generate_response(self, context: Dict[str, Any]) -> str:
        """
        사용자에게 전달할 응답 텍스트 생성

        Args:
            context: 현재 컨텍스트 (검색 결과, 상품 정보 등)

        Returns:
            str: 응답 텍스트
        """
        pass

    @abstractmethod
    async def should_delegate_to_flow(self, intent: IntentResult) -> Optional[str]:
        """
        Flow Engine 위임 여부 판단

        Args:
            intent: 의도 분석 결과

        Returns:
            str: 위임할 플로우 타입 (signup, checkout) 또는 None
        """
        pass


# ============================================================================
# TTS 모듈 인터페이스
# ============================================================================

class ITTSService(ABC):
    """음성 합성 (TTS) 서비스 인터페이스"""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        텍스트를 음성으로 변환

        Args:
            text: 변환할 텍스트

        Returns:
            bytes: 오디오 데이터
        """
        pass

    @abstractmethod
    async def synthesize_stream(self, text: str) -> AsyncGenerator[TTSChunk, None]:
        """
        텍스트를 스트리밍 음성으로 변환

        Args:
            text: 변환할 텍스트

        Yields:
            TTSChunk: 오디오 청크
        """
        pass

    @abstractmethod
    def get_voice_list(self) -> List[Dict[str, str]]:
        """
        사용 가능한 음성 목록 반환

        Returns:
            List[Dict]: 음성 정보 목록
        """
        pass


# ============================================================================
# OCR 모듈 인터페이스
# ============================================================================

class IOCRService(ABC):
    """이미지 인식 (OCR) 서비스 인터페이스"""

    @abstractmethod
    async def extract_text(self, image_data: bytes) -> OCRResult:
        """
        이미지에서 텍스트 추출

        Args:
            image_data: 이미지 데이터

        Returns:
            OCRResult: 추출된 텍스트 결과
        """
        pass

    @abstractmethod
    async def analyze_product_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        상품 이미지 분석 (색상, 형태, 특징)

        Args:
            image_data: 상품 이미지 데이터

        Returns:
            Dict: 분석 결과 (색상, 형태, 텍스트 등)
        """
        pass

    @abstractmethod
    async def recognize_keypad(self, image_data: bytes) -> Dict[str, str]:
        """
        보안 키패드 인식

        Args:
            image_data: 키패드 이미지 데이터

        Returns:
            Dict[str, str]: 위치별 숫자 매핑
        """
        pass


# ============================================================================
# Flow Engine 모듈 인터페이스
# ============================================================================

class IFlowEngine(ABC):
    """쇼핑 플로우 엔진 인터페이스"""

    @abstractmethod
    async def start_flow(self, flow_type: str, site: str, session: SessionState) -> FlowStep:
        """
        플로우 시작

        Args:
            flow_type: 플로우 타입 (signup, checkout)
            site: 쇼핑몰 사이트
            session: 세션 상태

        Returns:
            FlowStep: 첫 번째 단계
        """
        pass

    @abstractmethod
    async def next_step(self, session: SessionState, user_input: Dict[str, Any] = None) -> FlowStep:
        """
        다음 단계로 진행

        Args:
            session: 세션 상태
            user_input: 사용자 입력 데이터

        Returns:
            FlowStep: 다음 단계
        """
        pass

    @abstractmethod
    async def cancel_flow(self, session: SessionState) -> None:
        """
        플로우 취소

        Args:
            session: 세션 상태
        """
        pass

    @abstractmethod
    def get_available_flows(self, site: str) -> List[str]:
        """
        특정 사이트에서 사용 가능한 플로우 목록

        Args:
            site: 쇼핑몰 사이트

        Returns:
            List[str]: 플로우 타입 목록
        """
        pass

    @abstractmethod
    async def validate_step(self, step: FlowStep, user_input: Dict[str, Any]) -> bool:
        """
        단계 유효성 검증

        Args:
            step: 현재 단계
            user_input: 사용자 입력

        Returns:
            bool: 유효 여부
        """
        pass


# ============================================================================
# Session 모듈 인터페이스
# ============================================================================

class ISessionManager(ABC):
    """세션 관리 인터페이스"""

    @abstractmethod
    def create_session(self, user_id: Optional[str] = None) -> SessionState:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID (선택)

        Returns:
            SessionState: 생성된 세션
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            SessionState: 세션 또는 None
        """
        pass

    @abstractmethod
    def update_session(self, session_id: str, **kwargs) -> SessionState:
        """
        세션 업데이트

        Args:
            session_id: 세션 ID
            **kwargs: 업데이트할 필드

        Returns:
            SessionState: 업데이트된 세션
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
        """
        pass

    @abstractmethod
    def add_to_history(self, session_id: str, role: str, content: str) -> None:
        """
        대화 기록 추가

        Args:
            session_id: 세션 ID
            role: 역할 (user/assistant)
            content: 내용
        """
        pass

    @abstractmethod
    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        컨텍스트 값 조회

        Args:
            session_id: 세션 ID
            key: 키
            default: 기본값

        Returns:
            Any: 저장된 값 또는 기본값
        """
        pass

    @abstractmethod
    def set_context(self, session_id: str, key: str, value: Any) -> None:
        """
        컨텍스트 값 저장

        Args:
            session_id: 세션 ID
            key: 키
            value: 값
        """
        pass
