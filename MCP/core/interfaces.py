"""
모듈 인터페이스 정의

모든 모듈의 추상 인터페이스를 정의하여 느슨한 결합 보장
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass


# ============================================================================
# Audio 모듈 인터페이스
# ============================================================================

class IAudioRecorder(ABC):
    """오디오 녹음 인터페이스"""

    @abstractmethod
    def start_recording(self) -> None:
        """녹음 시작"""
        pass

    @abstractmethod
    def stop_recording(self) -> bytes:
        """
        녹음 종료 및 오디오 데이터 반환

        Returns:
            bytes: 녹음된 오디오 데이터 (WAV 형식)
        """
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        """
        녹음 중인지 확인

        Returns:
            bool: 녹음 중이면 True
        """
        pass


class IAudioPlayer(ABC):
    """오디오 재생 인터페이스"""

    @abstractmethod
    def play(self, audio_data: bytes) -> None:
        """
        오디오 재생

        Args:
            audio_data: 재생할 오디오 데이터
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """재생 중지"""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """
        재생 중인지 확인

        Returns:
            bool: 재생 중이면 True
        """
        pass


class IHotkeyManager(ABC):
    """핫키 관리 인터페이스"""

    @abstractmethod
    def register_hotkey(self, key: str, callback: Callable) -> None:
        """
        핫키 등록

        Args:
            key: 핫키 (예: 'v')
            callback: 핫키 눌렸을 때 호출할 함수
        """
        pass

    @abstractmethod
    def unregister_hotkey(self, key: str) -> None:
        """
        핫키 등록 해제

        Args:
            key: 등록 해제할 핫키
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """핫키 감지 시작"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """핫키 감지 종료"""
        pass


# ============================================================================
# Browser 모듈 인터페이스
# ============================================================================

@dataclass
class BrowserConfig:
    """브라우저 설정"""
    user_data_dir: Optional[str] = None
    debugging_port: int = 9222
    headless: bool = False
    window_size: tuple = (1280, 720)


class IBrowserController(ABC):
    """브라우저 제어 인터페이스"""

    @abstractmethod
    def launch_chrome(self, config: BrowserConfig) -> bool:
        """
        Chrome 브라우저 실행

        Args:
            config: 브라우저 설정

        Returns:
            bool: 성공 여부
        """
        pass

    @abstractmethod
    def get_cdp_url(self) -> Optional[str]:
        """
        Chrome DevTools Protocol WebSocket URL 반환

        Returns:
            str: CDP WebSocket URL 또는 None
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        브라우저가 실행 중인지 확인

        Returns:
            bool: 실행 중이면 True
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """브라우저 종료"""
        pass


# ============================================================================
# MCP 모듈 인터페이스
# ============================================================================

@dataclass
class MCPToolCall:
    """MCP 도구 호출 데이터"""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """MCP 도구 실행 결과"""
    call_id: Optional[str]
    success: bool
    result: Any
    error: Optional[str] = None


class IMCPServerManager(ABC):
    """MCP 서버 관리 인터페이스"""

    @abstractmethod
    def start_server(self) -> bool:
        """
        MCP 서버 프로세스 시작

        Returns:
            bool: 성공 여부
        """
        pass

    @abstractmethod
    def stop_server(self) -> None:
        """MCP 서버 프로세스 종료"""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        MCP 서버가 실행 중인지 확인

        Returns:
            bool: 실행 중이면 True
        """
        pass


class IMCPClient(ABC):
    """MCP 클라이언트 인터페이스"""

    @abstractmethod
    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """
        MCP 도구 호출

        Args:
            tool_call: 호출할 도구 정보

        Returns:
            MCPToolResult: 도구 실행 결과
        """
        pass

    @abstractmethod
    async def get_available_tools(self) -> list[str]:
        """
        사용 가능한 도구 목록 반환

        Returns:
            list[str]: 도구 이름 목록
        """
        pass


# ============================================================================
# Network 모듈 인터페이스
# ============================================================================

@dataclass
class ServerConfig:
    """서버 연결 설정"""
    ws_url: str
    auth_url: Optional[str] = None
    access_token: Optional[str] = None
    reconnect_interval: int = 5


class IWebSocketClient(ABC):
    """WebSocket 클라이언트 인터페이스"""

    @abstractmethod
    async def connect(self, config: ServerConfig) -> bool:
        """
        서버에 연결

        Args:
            config: 서버 연결 설정

        Returns:
            bool: 연결 성공 여부
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """서버 연결 해제"""
        pass

    @abstractmethod
    async def send_audio(self, audio_data: bytes) -> None:
        """
        오디오 데이터 전송

        Args:
            audio_data: 전송할 오디오 데이터
        """
        pass

    @abstractmethod
    async def send_mcp_result(self, result: MCPToolResult) -> None:
        """
        MCP 실행 결과 전송

        Args:
            result: MCP 도구 실행 결과
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        연결 상태 확인

        Returns:
            bool: 연결되어 있으면 True
        """
        pass


class IAuthManager(ABC):
    """인증 관리 인터페이스"""

    @abstractmethod
    async def authenticate(self) -> Optional[str]:
        """
        인증 수행

        Returns:
            str: access token 또는 None
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> Optional[str]:
        """
        토큰 갱신

        Returns:
            str: 새로운 access token 또는 None
        """
        pass

    @abstractmethod
    def get_access_token(self) -> Optional[str]:
        """
        현재 access token 반환

        Returns:
            str: access token 또는 None
        """
        pass


# ============================================================================
# Session 모듈 인터페이스
# ============================================================================

@dataclass
class SessionState:
    """세션 상태"""
    user_id: Optional[str] = None
    current_site: Optional[str] = None
    current_flow: Optional[str] = None
    flow_step: int = 0
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ISessionManager(ABC):
    """세션 관리 인터페이스"""

    @abstractmethod
    def get_state(self) -> SessionState:
        """
        현재 세션 상태 반환

        Returns:
            SessionState: 현재 세션 상태
        """
        pass

    @abstractmethod
    def update_state(self, **kwargs) -> None:
        """
        세션 상태 업데이트

        Args:
            **kwargs: 업데이트할 상태 필드
        """
        pass

    @abstractmethod
    def set_context(self, key: str, value: Any) -> None:
        """
        컨텍스트에 값 저장

        Args:
            key: 키
            value: 값
        """
        pass

    @abstractmethod
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        컨텍스트에서 값 가져오기

        Args:
            key: 키
            default: 기본값

        Returns:
            Any: 저장된 값 또는 기본값
        """
        pass

    @abstractmethod
    def clear_context(self) -> None:
        """컨텍스트 초기화"""
        pass

    @abstractmethod
    def save_to_file(self, filepath: str) -> None:
        """
        세션 상태를 파일에 저장

        Args:
            filepath: 저장할 파일 경로
        """
        pass

    @abstractmethod
    def load_from_file(self, filepath: str) -> bool:
        """
        파일에서 세션 상태 로드

        Args:
            filepath: 로드할 파일 경로

        Returns:
            bool: 성공 여부
        """
        pass


# ============================================================================
# UI 모듈 인터페이스
# ============================================================================

@dataclass
class AppStatus:
    """앱 상태"""
    status: str  # 예: "idle", "recording", "processing", "playing"
    message: Optional[str] = None


class IUIManager(ABC):
    """UI 관리 인터페이스"""

    @abstractmethod
    def show_tray_icon(self) -> None:
        """시스템 트레이 아이콘 표시"""
        pass

    @abstractmethod
    def hide_tray_icon(self) -> None:
        """시스템 트레이 아이콘 숨김"""
        pass

    @abstractmethod
    def update_status(self, status: AppStatus) -> None:
        """
        앱 상태 업데이트

        Args:
            status: 새로운 앱 상태
        """
        pass

    @abstractmethod
    def show_notification(self, title: str, message: str) -> None:
        """
        시스템 알림 표시

        Args:
            title: 알림 제목
            message: 알림 메시지
        """
        pass

    @abstractmethod
    def request_exit(self) -> None:
        """앱 종료 요청"""
        pass
