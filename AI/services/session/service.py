"""
Session Manager 서비스 구현

세션 상태, 대화 컨텍스트, 즐겨찾기 관리
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from core.interfaces import ISessionManager, SessionState

logger = logging.getLogger(__name__)


class SessionManager(ISessionManager):
    """
    세션 관리자

    Features:
    - 세션 생성/조회/업데이트/삭제
    - 대화 기록 관리
    - 검색 기록 및 컨텍스트 관리
    - 즐겨찾기 관리 (선택)
    """

    def __init__(self, session_timeout_minutes: int = 30):
        self._sessions: Dict[str, SessionState] = {}
        self._session_timestamps: Dict[str, datetime] = {}
        self._timeout = timedelta(minutes=session_timeout_minutes)

    async def initialize(self):
        """세션 관리자 초기화"""
        logger.info("Session Manager initialized")

    def create_session(self, user_id: Optional[str] = None, session_id: Optional[str] = None) -> SessionState:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID (선택)
            session_id: 세션 ID (선택, 없으면 자동 생성)

        Returns:
            SessionState: 생성된 세션
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            search_history=[],
            cart_items=[],
            context={},
            conversation_history=[]
        )

        self._sessions[session_id] = session
        self._session_timestamps[session_id] = datetime.now()

        logger.info(f"Session created: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            SessionState: 세션 또는 None
        """
        # 만료 체크
        if self._is_expired(session_id):
            self.delete_session(session_id)
            return None

        session = self._sessions.get(session_id)
        if session:
            self._session_timestamps[session_id] = datetime.now()

        return session

    def update_session(self, session_id: str, **kwargs) -> SessionState:
        """
        세션 업데이트

        Args:
            session_id: 세션 ID
            **kwargs: 업데이트할 필드

        Returns:
            SessionState: 업데이트된 세션
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        self._session_timestamps[session_id] = datetime.now()
        logger.debug(f"Session updated: {session_id}, fields: {list(kwargs.keys())}")

        return session

    def delete_session(self, session_id: str) -> None:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._session_timestamps[session_id]
            logger.info(f"Session deleted: {session_id}")

    def add_to_history(self, session_id: str, role: str, content: str) -> None:
        """
        대화 기록 추가

        Args:
            session_id: 세션 ID
            role: 역할 (user/assistant)
            content: 내용
        """
        session = self.get_session(session_id)
        if not session:
            return

        session.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # 최대 기록 수 제한 (예: 100개)
        if len(session.conversation_history) > 100:
            session.conversation_history = session.conversation_history[-100:]

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
        session = self.get_session(session_id)
        if not session:
            return default

        return session.context.get(key, default)

    def set_context(self, session_id: str, key: str, value: Any) -> None:
        """
        컨텍스트 값 저장

        Args:
            session_id: 세션 ID
            key: 키
            value: 값
        """
        session = self.get_session(session_id)
        if not session:
            return

        session.context[key] = value
        logger.debug(f"Context set: {session_id}/{key}")

    def add_search_history(self, session_id: str, query: str) -> None:
        """검색 기록 추가"""
        session = self.get_session(session_id)
        if not session:
            return

        session.search_history.append(query)
        # 최대 검색 기록 수 제한
        if len(session.search_history) > 50:
            session.search_history = session.search_history[-50:]

    def add_cart_item(self, session_id: str, item: Dict[str, Any]) -> None:
        """장바구니 아이템 추가"""
        session = self.get_session(session_id)
        if not session:
            return

        session.cart_items.append(item)

    def remove_cart_item(self, session_id: str, item_id: str) -> None:
        """장바구니 아이템 제거"""
        session = self.get_session(session_id)
        if not session:
            return

        session.cart_items = [
            item for item in session.cart_items
            if item.get("id") != item_id
        ]

    def clear_cart(self, session_id: str) -> None:
        """장바구니 비우기"""
        session = self.get_session(session_id)
        if session:
            session.cart_items = []

    def _is_expired(self, session_id: str) -> bool:
        """세션 만료 여부 확인"""
        timestamp = self._session_timestamps.get(session_id)
        if not timestamp:
            return True

        return datetime.now() - timestamp > self._timeout

    def cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리"""
        expired = [
            sid for sid in self._sessions
            if self._is_expired(sid)
        ]

        for sid in expired:
            self.delete_session(sid)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    def get_active_session_count(self) -> int:
        """활성 세션 수"""
        return len(self._sessions)

    async def shutdown(self):
        """리소스 정리"""
        self._sessions.clear()
        self._session_timestamps.clear()
        logger.info("Session Manager shutdown")