#!/usr/bin/env python3
"""
MCP 테스트용 API 서버

test_command_cli.py에서 생성된 명령을 받아 Playwright로 실행합니다.

사용법:
    1. 이 서버 실행 (Chrome 자동 실행):
       cd c:\\ssafy\\공통\\AI
       python services/llm/tests/mcp_api_server.py
    
    2. test_command_cli.py 실행:
       python services/llm/tests/test_command_cli.py --exec
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add parent directory to path for MCP imports
project_root = Path(__file__).resolve().parents[3]
common_root = project_root.parent
mcp_root = common_root / "MCP"
sys.path.insert(0, str(mcp_root))

from browser.chrome_utils import ensure_chrome_env, find_chrome_path, get_env_value
from browser.action_utils import (
    click_text as click_text_util,
    get_visible_buttons as get_visible_buttons_util,
)
from mcp.tool_utils import normalize_tool_call, resolve_frame_context

# Playwright
try:
    from playwright.async_api import async_playwright, Browser, Page, Playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("⚠️ playwright 모듈이 없습니다. pip install playwright && playwright install chromium")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic 모델
# =============================================================================

class CommandItem(BaseModel):
    action: str
    args: Dict[str, Any] = {}
    desc: str = ""


class ExecuteRequest(BaseModel):
    type: str = "tool_calls"
    data: Dict[str, Any] = {}


class ExecuteResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]] = []
    error: Optional[str] = None


# =============================================================================
# 브라우저 관리
# =============================================================================

class BrowserManager:
    """Playwright 브라우저 관리 - 항상 최신 활성 페이지 자동 추적"""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._chrome_process: Optional[subprocess.Popen] = None
        self._chrome_started = False
        self._env_path = mcp_root / ".env"

        chrome_path = ensure_chrome_env(self._env_path)
        if chrome_path:
            os.environ.setdefault("CHROME_PATH", chrome_path)

        port_value = (
            os.getenv("CHROME_DEBUG_PORT")
            or get_env_value(self._env_path, "CHROME_DEBUG_PORT")
            or os.getenv("CDP_PORT")
            or "9222"
        )
        try:
            self._chrome_port = int(port_value)
        except ValueError:
            self._chrome_port = 9222

        user_dir_value = (
            os.getenv("CHROME_USER_DATA_DIR")
            or get_env_value(self._env_path, "CHROME_USER_DATA_DIR")
            or os.getenv("CDP_USER_DATA_DIR")
            or ""
        )
        if user_dir_value:
            user_dir_path = Path(user_dir_value)
            if not user_dir_path.is_absolute():
                user_dir_path = mcp_root / user_dir_path
            self._user_data_dir = user_dir_path
        else:
            self._user_data_dir = mcp_root / ".mcp_chrome_profile"

        self._cdp_url = f"http://127.0.0.1:{self._chrome_port}"

    @property
    def is_connected(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    @property
    def _page(self) -> Optional[Page]:
        """항상 가장 최근(마지막) 페이지 반환 - 새 탭/창 열리면 자동 전환"""
        if not self._browser:
            return None
        all_pages = []
        for ctx in self._browser.contexts:
            all_pages.extend(ctx.pages)
        return all_pages[-1] if all_pages else None

    @property
    def current_url(self) -> Optional[str]:
        page = self._page
        return page.url if page else None

    def get_all_pages(self) -> List[Dict[str, Any]]:
        """모든 열린 페이지 목록 반환"""
        pages = []
        if not self._browser:
            return pages
        current = self._page
        for ctx in self._browser.contexts:
            for page in ctx.pages:
                pages.append({
                    "index": len(pages),
                    "url": page.url,
                    "title": page.url.split("/")[2] if "/" in page.url else page.url,
                    "is_current": page == current
                })
        return pages

    def _build_chrome_args(self, chrome_path: str) -> List[str]:
        args = [
            chrome_path,
            f"--remote-debugging-port={self._chrome_port}",
            f"--user-data-dir={self._user_data_dir.resolve()}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--window-size=1280,720",
        ]
        return args

    async def _start_chrome(self) -> bool:
        if self._chrome_process and self._chrome_process.poll() is None:
            return True

        chrome_path = find_chrome_path()
        if not chrome_path:
            logger.error("Chrome executable not found")
            return False

        self._user_data_dir.mkdir(parents=True, exist_ok=True)
        args = self._build_chrome_args(chrome_path)
        logger.info(f"Starting Chrome with args: {' '.join(args)}")

        try:
            self._chrome_process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self._chrome_started = True
            return True
        except Exception as e:
            logger.error(f"Failed to start Chrome: {e}")
            return False

    async def _try_connect(self, retries: int = 20, delay: float = 0.5) -> bool:
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        last_error = None
        for _ in range(retries):
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(self._cdp_url)
                return True
            except Exception as e:
                last_error = e
                await asyncio.sleep(delay)

        if last_error:
            logger.error(f"브라우저 연결 실패: {last_error}")
        return False

    async def connect(self, auto_start: bool = True) -> bool:
        """CDP로 Chrome에 연결 (필요 시 Chrome 자동 실행)"""
        if not HAS_PLAYWRIGHT:
            return False

        if self.is_connected:
            return True

        try:
            if auto_start:
                ensure_chrome_env(self._env_path)
            # 이미 실행된 Chrome에 먼저 연결 시도
            connected = await self._try_connect(retries=2, delay=0.5)
            if not connected and auto_start:
                started = await self._start_chrome()
                if not started:
                    return False
                connected = await self._try_connect(retries=20, delay=0.5)

            if not connected:
                return False

            # 페이지가 없으면 새로 생성
            if not self._page:
                context = await self._browser.new_context()
                await context.new_page()

            logger.info(f"브라우저 연결 성공: {self.current_url}")
            return True
        except Exception as e:
            logger.error(f"브라우저 연결 실패: {e}")
            return False

    async def disconnect(self):
        """연결 해제"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        if self._chrome_process and self._chrome_started:
            try:
                self._chrome_process.terminate()
                self._chrome_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._chrome_process.kill()
            except Exception:
                pass
        self._chrome_process = None
        self._chrome_started = False
        logger.info("브라우저 연결 해제")

    async def execute_command(self, cmd: CommandItem) -> Dict[str, Any]:
        """단일 명령 실행 - 항상 현재 활성 페이지에서 실행"""
        page = self._page
        if not page:
            return {"success": False, "error": "페이지 없음", "desc": cmd.desc}

        action, args = normalize_tool_call(cmd.action, cmd.args)

        try:
            result = None

            if action == "navigate_to_url":
                url = args.get("url", "")
                await page.goto(url, wait_until="domcontentloaded")
                result = f"이동: {url}"

            elif action == "click_element":
                selector = args.get("selector", "")
                context_type, context, error = resolve_frame_context(
                    page,
                    frame_selector=args.get("frame_selector"),
                    frame_name=args.get("frame_name"),
                    frame_url=args.get("frame_url"),
                    frame_index=args.get("frame_index"),
                )
                if error:
                    return {"success": False, "error": error, "desc": cmd.desc}
                if context_type == "frame_locator":
                    locator = context.locator(selector)
                    await locator.click(timeout=5000)
                else:
                    await context.click(selector, timeout=5000)
                result = f"클릭: {selector}"

            elif action == "fill_input":
                selector = args.get("selector", "")
                text = args.get("value", "")
                context_type, context, error = resolve_frame_context(
                    page,
                    frame_selector=args.get("frame_selector"),
                    frame_name=args.get("frame_name"),
                    frame_url=args.get("frame_url"),
                    frame_index=args.get("frame_index"),
                )
                if error:
                    return {"success": False, "error": error, "desc": cmd.desc}
                if context_type == "frame_locator":
                    locator = context.locator(selector)
                    await locator.fill(text)
                else:
                    await context.fill(selector, text)
                result = f"입력: {text}"

            elif action == "press_key":
                selector = args.get("selector", "")
                key = args.get("key", "Enter")
                context_type, context, error = resolve_frame_context(
                    page,
                    frame_selector=args.get("frame_selector"),
                    frame_name=args.get("frame_name"),
                    frame_url=args.get("frame_url"),
                    frame_index=args.get("frame_index"),
                )
                if error:
                    return {"success": False, "error": error, "desc": cmd.desc}
                if context_type == "frame_locator":
                    locator = context.locator(selector)
                    await locator.press(key)
                else:
                    await context.press(selector, key)
                result = f"키 입력: {key}"

            elif action == "wait":
                ms = args.get("ms", 1000)
                await asyncio.sleep(ms / 1000)
                result = f"대기: {ms}ms"

            elif action == "scroll":
                direction = args.get("direction", "down")
                amount = args.get("amount", 500)
                if direction == "down":
                    await page.evaluate(f"window.scrollBy(0, {amount})")
                else:
                    await page.evaluate(f"window.scrollBy(0, -{amount})")
                result = f"스크롤: {direction}"

            elif action == "get_visible_buttons":
                buttons = await get_visible_buttons_util(page)
                result = buttons

            elif action == "take_screenshot":
                path = args.get("path", "screenshot.png")
                await page.screenshot(path=path)
                result = f"스크린샷: {path}"

            elif action == "click_text":
                text = args.get("text", "")
                click_result = await click_text_util(page, text)
                if click_result["success"]:
                    result = click_result["result"]
                else:
                    return {"success": False, "error": click_result["error"], "desc": cmd.desc}
            
            else:
                return {"success": False, "error": f"알 수 없는 액션: {action}", "desc": cmd.desc}
            
            return {"success": True, "result": result, "desc": cmd.desc}
        
        except Exception as e:
            return {"success": False, "error": str(e), "desc": cmd.desc}


# =============================================================================
# FastAPI 앱
# =============================================================================

browser = BrowserManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MCP Test API Server 시작")
    ensure_chrome_env(mcp_root / ".env")
    await browser.connect(auto_start=True)
    yield
    await browser.disconnect()
    logger.info("MCP Test API Server 종료")


app = FastAPI(
    title="MCP Test API Server",
    description="test_command_cli.py 테스트용 API 서버",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "MCP Test API Server",
        "status": "running",
        "browser_connected": browser.is_connected
    }


@app.post("/start")
async def start_browser():
    """브라우저 연결"""
    success = await browser.connect(auto_start=True)
    return {"success": success}


@app.get("/status")
async def get_status():
    """상태 확인"""
    return {
        "browser_connected": browser.is_connected,
        "page_ready": browser._page is not None,
        "current_url": browser.current_url
    }


@app.get("/url")
async def get_url():
    """현재 URL"""
    return {"url": browser.current_url}


@app.get("/pages")
async def get_pages():
    """열린 모든 페이지 목록 (현재 활성 페이지 표시)"""
    pages = browser.get_all_pages()
    return {"success": True, "pages": pages, "count": len(pages)}


@app.get("/buttons")
async def get_buttons():
    """현재 활성 페이지의 클릭 가능한 요소들 조회"""
    page = browser._page
    if not browser.is_connected or not page:
        return {"success": False, "error": "Browser not connected", "buttons": []}

    buttons = await get_visible_buttons_util(page)
    return {"success": True, "buttons": buttons, "count": len(buttons)}


@app.post("/execute", response_model=ExecuteResponse)
async def execute_commands(request: ExecuteRequest):
    """명령 실행"""
    if not browser.is_connected:
        return ExecuteResponse(success=False, error="브라우저 연결 안됨")
    
    commands_data = request.data.get("commands", [])
    if not commands_data:
        return ExecuteResponse(success=False, error="명령 없음")
    
    results = []
    all_success = True
    
    for cmd_data in commands_data:
        cmd = CommandItem(**cmd_data)
        result = await browser.execute_command(cmd)
        results.append(result)
        if not result.get("success"):
            all_success = False
    
    return ExecuteResponse(success=all_success, results=results)


@app.post("/stop")
async def stop_browser():
    """브라우저 연결 해제"""
    await browser.disconnect()
    return {"success": True}


# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("MCP Test API Server")
    print("=" * 60)
    print("Chrome은 자동으로 CDP 모드로 실행됩니다.")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
