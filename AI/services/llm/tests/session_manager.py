"""
세션 및 대화 기록 관리 모듈

사용자 세션 상태, 대화 기록, 현재 URL 등을 관리합니다.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class SessionState:
    """사용자 세션 상태"""
    session_id: str
    current_url: str = "https://www.coupang.com/"
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str):
        """대화 기록 추가"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 최근 20개만 유지 (메모리 관리)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def clear_history(self):
        """대화 기록 초기화"""
        self.conversation_history = []
    
    def get_recent_messages(self, n: int = 10) -> List[Dict[str, str]]:
        """최근 N개 메시지 반환"""
        return self.conversation_history[-n:] if self.conversation_history else []
    
    def update_url(self, url: str):
        """현재 URL 업데이트"""
        self.current_url = url


class SessionManager:
    """세션 관리자 (멀티 세션 지원)"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
    
    def create_session(self, session_id: str, initial_url: str = "https://www.coupang.com/") -> SessionState:
        """새 세션 생성"""
        session = SessionState(
            session_id=session_id,
            current_url=initial_url
        )
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """세션 가져오기"""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str, initial_url: str = "https://www.coupang.com/") -> SessionState:
        """세션 가져오기 또는 생성"""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id, initial_url)
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """모든 세션 ID 목록"""
        return list(self._sessions.keys())
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """오래된 세션 정리"""
        now = datetime.now()
        to_delete = []
        
        for session_id, session in self._sessions.items():
            age = (now - session.created_at).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            del self._sessions[session_id]
        
        return len(to_delete)


# 싱글톤 인스턴스
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """SessionManager 싱글톤 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
