"""
최소 상태 표시 창

작은 창으로 현재 앱 상태를 표시
"""

import tkinter as tk
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MiniWindow:
    """최소 상태 표시 창"""

    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.status_label: Optional[tk.Label] = None
        self.message_label: Optional[tk.Label] = None
        self.current_status = "대기 중"
        self.current_message = "Hotkey: space 스페이스"
        self.exit_callback = None
        self.device_select_callback = None
        self.device_button = None

    def create_window(self):
        """창 생성"""
        self.root = tk.Tk()
        self.root.title("MCP App")

        # 창 크기 및 위치 설정
        window_width = 250
        window_height = 140

        # 화면 우측 하단에 배치
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - window_width - 50
        y = screen_height - window_height - 100

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 항상 위에 표시
        self.root.attributes("-topmost", True)

        # 창 닫기 버튼(X) 클릭 시 종료 콜백 호출
        self.root.protocol("WM_DELETE_WINDOW", self._request_exit)

        # 창 스타일
        self.root.configure(bg="#2C3E50")

        # 프레임
        frame = tk.Frame(self.root, bg="#2C3E50", padx=20, pady=20)
        frame.pack(expand=True, fill=tk.BOTH)

        # 상태 이모지 및 텍스트
        self.status_label = tk.Label(
            frame,
            text=f"🎤 {self.current_status}",
            font=("Segoe UI", 14, "bold"),
            fg="#ECF0F1",
            bg="#2C3E50"
        )
        self.status_label.pack(pady=(0, 10))

        # 메시지
        self.message_label = tk.Label(
            frame,
            text=self.current_message,
            font=("Segoe UI", 10),
            fg="#BDC3C7",
            bg="#2C3E50"
        )
        self.message_label.pack()
        self.device_button = tk.Button(
            frame,
            text="\uc7a5\uce58 \ubcc0\uacbd",
            font=("Segoe UI", 9),
            command=self._request_device_select
        )
        self.device_button.pack(pady=(8, 0))

        logger.info("Mini window created")

    def update_status(self, status: str, message: str = ""):
        """
        상태 업데이트

        Args:
            status: 상태 텍스트 (예: "대기 중", "녹음 중", "처리 중")
            message: 추가 메시지
        """
        self.current_status = status
        self.current_message = message

        if self.root and self.status_label and self.message_label:
            # 상태에 따라 이모지 변경
            emoji = self._get_emoji(status)
            self.status_label.config(text=f"{emoji} {status}")
            self.message_label.config(text=message)
            logger.debug(f"Status updated: {status} - {message}")

    def _get_emoji(self, status: str) -> str:
        """상태에 맞는 이모지 반환"""
        status_lower = status.lower()
        if "대기" in status_lower or "idle" in status_lower:
            return "🎤"
        elif "녹음" in status_lower or "recording" in status_lower:
            return "🔴"
        elif "처리" in status_lower or "processing" in status_lower:
            return "⚙️"
        elif "재생" in status_lower or "playing" in status_lower:
            return "🔊"
        elif "완료" in status_lower or "done" in status_lower:
            return "✅"
        elif "오류" in status_lower or "error" in status_lower:
            return "❌"
        else:
            return "ℹ️"

    def show(self):
        """창 표시"""
        if not self.root:
            self.create_window()

        self.root.deiconify()
        logger.info("Mini window shown")

    def hide(self):
        """창 숨김"""
        if self.root:
            self.root.withdraw()
            logger.info("Mini window hidden")

    def run(self):
        """메인 루프 실행 (블로킹)"""
        if not self.root:
            self.create_window()

        logger.info("Starting mini window main loop")
        self.root.mainloop()

    def update(self):
        """창 업데이트 (비블로킹)"""
        if self.root:
            self.root.update()

    def destroy(self):
        """창 종료"""
        if self.root:
            try:
                self.root.quit()
                logger.info("Mini window destroyed")
            except Exception as e:
                logger.warning(f"Error destroying window: {e}")
            self.root = None

    def set_device_select_callback(self, callback):
        """
        장치 선택 콜백 설정

        Args:
            callback: 장치 변경 버튼 클릭 시 호출되는 함수
        """
        self.device_select_callback = callback

    def _request_device_select(self):
        """장치 선택 요청"""
        if self.device_select_callback:
            self.device_select_callback()

    def set_exit_callback(self, callback):
        """
        종료 콜백 설정

        Args:
            callback: 종료 버튼 클릭 시 호출할 함수
        """
        self.exit_callback = callback

    def _request_exit(self):
        """종료 요청"""
        logger.info("Exit requested from mini window")
        if self.exit_callback:
            self.exit_callback()
        else:
            self.destroy()
