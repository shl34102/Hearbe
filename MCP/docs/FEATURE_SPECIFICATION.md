# MCP 데스크탑 앱 기능 명세서

> 기능 목록 및 상세 정의

---

## 핵심 기능 목록

| 번호 | 기능명 | 설명 | 담당자 |
|------|--------|------|--------|
| MCP-01 | 음성 녹음 | V키 핫키로 마이크 녹음 시작/종료 | 김민찬 |
| MCP-02 | 음성 재생 | TTS 오디오 재생 | 김민찬 |
| MCP-03 | 브라우저 실행 | Chrome 자동 실행 (CDP 활성화) | 김재환 |
| MCP-04 | 브라우저 제어 | MCP 도구로 웹 페이지 조작 | 김재환 |
| MCP-05 | 서버 통신 | WebSocket으로 AI 서버와 실시간 통신 | 김민찬 |
| MCP-06 | 세션 관리 | 현재 작업 상태 추적 | 김민찬 |
| MCP-07 | 상태 표시 | 최소 UI로 현재 상태 표시 | 김민찬 |
| MCP-08 | 텍스트 입력 (테스트용) | 콘솔에서 직접 텍스트 입력하여 AI 서버로 전송 | 김재환 |
| MCP-09 | WS 게이트웨이 | 세션 생성/상태(status) 송수신/재연결 정책 | 김민찬 |

---

## 전체 동작 플로우

### 일반 플로우
```
MCP앱(음성녹음) → AI서버(STT→LLM판단→TTS) → MCP앱(음성출력)
       ↓                                        ↓
  다시 음성녹음 ←──────────────────────────────┘
       ↓
AI서버(STT→명령판단) → MCP앱(MCP명령 실행) → 브라우저 제어
```

### 플로우/DB 조회 필요 시
```
AI서버 ──→ 백엔드(웹서버) ──→ DB
        (플로우 조회)    (사용자 데이터)
```

---

## F-01: 음성 녹음

### 기능 설명
V키를 누르면 녹음 시작, 떼면 녹음 종료. 녹음된 오디오는 서버로 전송.

### 상세 동작
1. V키 누름 감지 → 녹음 시작
2. 마이크로부터 오디오 캡처 (16kHz, 모노, 16-bit PCM)
3. V키 뗌 감지 → 녹음 종료
4. 오디오 데이터를 이벤트로 발행

### 담당 모듈
- `audio/hotkey.py` - 핫키 감지
- `audio/recorder.py` - 녹음 처리

### 발행 이벤트
- `HOTKEY_PRESSED` - V키 눌림
- `RECORDING_STARTED` - 녹음 시작
- `RECORDING_STOPPED` - 녹음 종료
- `AUDIO_READY` - 오디오 데이터 준비 (data: bytes)

### 환경 변수
```env
HOTKEY=v
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_CHUNK_SIZE=1024
```

---

## F-02: 음성 재생

### 기능 설명
서버로부터 받은 TTS 오디오를 스피커로 재생.

### 상세 동작
1. 서버로부터 TTS 오디오 수신
2. MP3/WAV 오디오 재생
3. 재생 완료 후 이벤트 발행

### 담당 모듈
- `audio/player.py` - 오디오 재생

### 구독 이벤트
- `TTS_AUDIO_RECEIVED` - TTS 음성 수신 (data: bytes)

### 발행 이벤트
- `TTS_PLAYBACK_FINISHED` - 재생 완료

---

## F-03: 브라우저 실행

### 기능 설명
앱 시작 시 Chrome 브라우저를 CDP(Chrome DevTools Protocol) 모드로 자동 실행.

### 상세 동작
1. Chrome 실행 파일 탐색
2. `--remote-debugging-port=9222` 옵션으로 실행
3. 사용자 프로필 디렉토리 지정 (로그인 유지)
4. CDP WebSocket URL 획득
5. 브라우저 준비 완료 이벤트 발행

> **TODO**: 추후 자사 웹사이트 구현 완료 시, 브라우저 실행 후 자사 웹사이트로 자동 리다이렉트 기능 추가

### 담당 모듈
- `browser/launcher.py` - Chrome 실행
- `browser/cdp_client.py` - CDP 연결

### 발행 이벤트
- `BROWSER_READY` - Chrome 실행 완료
  ```python
  {
    "cdp_url": "ws://127.0.0.1:9222/devtools/browser/...",
    "process_id": 12345
  }
  ```

### 환경 변수
```env
BROWSER_EXECUTABLE_PATH=          # 비어있으면 자동 탐색
BROWSER_CDP_PORT=9222
BROWSER_USER_DATA_DIR=./chrome_profile
BROWSER_HEADLESS=false
```

### Chrome 실행 옵션
```bash
chrome.exe \
  --remote-debugging-port=9222 \
  --user-data-dir=./chrome_profile \
  --no-first-run \
  --no-default-browser-check
```

---

## F-04: 브라우저 제어

### 기능 설명
MCP 서버를 통해 Playwright로 브라우저를 자동 제어.

### 상세 동작
1. MCP 서버 프로세스 시작
2. 서버로부터 도구 호출 요청 수신
3. Playwright로 브라우저 조작 실행
4. 실행 결과 반환

MCP (Model Context Protocol) 는 AI 모델이 외부 도구(브라우저, 파일 시스템 등)를 호출할 수 있게 해주는 프로토콜입니다.

이 프로젝트에서 MCP 서버는 AI 서버와 브라우저 사이의 중간 다리 역할을 합니다:

### 담당 모듈
- `mcp/server_manager.py` - MCP 서버 관리
- `mcp/playwright_mcp_server.py` - Playwright 도구 구현
- `mcp/client.py` - MCP 클라이언트

### 지원 도구

#### navigate_to_url
특정 URL로 이동
```python
{
  "tool_name": "navigate_to_url",
  "arguments": {
    "url": "https://www.coupang.com"  # required
  }
}
# 반환: {"success": true, "current_url": "..."}
```

#### click_element
요소 클릭
```python
{
  "tool_name": "click_element",
  "arguments": {
    "selector": "#searchBtn",  # required, CSS 선택자
    "wait_timeout": 5000       # optional, ms
  }
}
# 반환: {"success": true, "element_found": true}
```

#### fill_input
입력 필드 채우기
```python
{
  "tool_name": "fill_input",
  "arguments": {
    "selector": "#searchKeyword",  # required
    "value": "무선 이어폰"          # required
  }
}
# 반환: {"success": true}
```

#### get_text
요소의 텍스트 추출
```python
{
  "tool_name": "get_text",
  "arguments": {
    "selector": ".product-title"  # required
  }
}
# 반환: {"success": true, "text": "상품명"}
```

#### take_screenshot
스크린샷 캡처
```python
{
  "tool_name": "take_screenshot",
  "arguments": {
    "full_page": false  # optional
  }
}
# 반환: {"success": true, "screenshot_base64": "..."}
```

#### scroll
페이지 스크롤
```python
{
  "tool_name": "scroll",
  "arguments": {
    "direction": "down",  # required: "up" | "down"
    "amount": 500         # optional, px
  }
}
# 반환: {"success": true}
```

### 구독 이벤트
- `MCP_TOOL_CALL` - 도구 호출 요청
  ```python
  {
    "request_id": "req_12345",
    "tool_name": "navigate_to_url",
    "arguments": {"url": "https://..."}
  }
  ```

### 발행 이벤트
- `MCP_SERVER_READY` - MCP 서버 시작 완료
- `MCP_RESULT` - 도구 실행 결과
  ```python
  {
    "request_id": "req_12345",
    "success": true,
    "result": {...},
    "error": null
  }
  ```

### 환경 변수
```env
MCP_SERVER_COMMAND=python mcp/playwright_mcp_server.py
MCP_SERVER_TIMEOUT=10
MCP_TOOL_TIMEOUT=60
```

---

## F-05: 서버 통신

### 기능 설명
WebSocket으로 AI 서버와 실시간 양방향 통신.

### 상세 동작
1. 앱 시작 시 WebSocket 연결
2. 오디오 데이터 서버로 전송
3. 서버로부터 STT/LLM/TTS 결과 수신
4. 연결 끊김 시 자동 재연결

### 담당 모듈
- `network/ws_client.py` - WebSocket 클라이언트

### 메시지 타입 (Client → Server)

#### audio_chunk
오디오 데이터 전송
```json
{
  "type": "audio_chunk",
  "data": {
    "audio": "base64_encoded_audio",
    "sample_rate": 16000,
    "channels": 1,
    "sequence": 123
  },
  "session_id": "uuid-v4"
}
```

#### mcp_result
MCP 도구 실행 결과 전송
```json
{
  "type": "mcp_result",
  "data": {
    "request_id": "req_12345",
    "success": true,
    "result": {...}
  }
}
```

### 메시지 타입 (Server → Client)

#### stt_result
STT 결과 수신
```json
{
  "type": "stt_result",
  "data": {
    "text": "쿠팡에서 우유 검색해줘",
    "confidence": 0.95
  }
}
```

#### llm_command
LLM 명령 수신
```json
{
  "type": "llm_command",
  "data": {
    "intent": "search_product",
    "site": "coupang",
    "parameters": {"keyword": "우유"}
  }
}
```

#### tool_call
MCP 도구 호출 요청 수신
```json
{
  "type": "tool_call",
  "data": {
    "request_id": "req_12345",
    "tool_name": "navigate_to_url",
    "arguments": {"url": "https://www.coupang.com"}
  }
}
```

#### tts_audio
TTS 오디오 수신
```json
{
  "type": "tts_audio",
  "data": {
    "audio": "base64_encoded_audio",
    "text": "검색 결과를 찾았습니다.",
    "format": "mp3"
  }
}
```

#### flow_step
플로우 단계 진행 알림
```json
{
  "type": "flow_step",
  "data": {
    "flow_id": "coupang_checkout",
    "current_step": 2,
    "total_steps": 5,
    "prompt": "배송지 주소를 말씀해주세요."
  }
}
```

### 구독 이벤트
- `AUDIO_READY` - 오디오 데이터 → 서버로 전송
- `MCP_RESULT` - MCP 결과 → 서버로 전송

### 발행 이벤트
- `STT_RESULT_RECEIVED` - STT 결과 수신 (data: str)
- `LLM_COMMAND_RECEIVED` - LLM 명령 수신 (data: dict)
- `MCP_TOOL_CALL` - 도구 호출 요청 수신 (data: dict)
- `TTS_AUDIO_RECEIVED` - TTS 오디오 수신 (data: bytes)

### 환경 변수
```env
WS_URL=ws://localhost:8000/ws
WS_RECONNECT_DELAY=5
WS_MAX_RETRIES=10
```

### 재연결 로직
```python
retry_count = 0
while retry_count < max_retries:
    try:
        await connect()
        return
    except:
        retry_count += 1
        await asyncio.sleep(reconnect_delay)
```

---

## F-06: 세션 관리

### 기능 설명
현재 사용자 세션 상태(사이트, 작업, 쿼리 등)를 추적.

### 상세 동작
1. 모든 주요 이벤트 구독
2. 이벤트 발생 시 세션 상태 자동 업데이트
3. 상태 변경 시 이벤트 발행
4. (선택) 파일로 상태 저장

### 담당 모듈
- `session/state_manager.py` - 세션 관리

### 세션 데이터 구조
```python
{
  "session_id": "uuid-v4",
  "current_site": "coupang",      # coupang | naver | elevenst
  "current_task": "idle",         # idle | recording | searching | checkout
  "last_query": "우유",
  "flow": {
    "flow_id": "coupang_checkout",
    "current_step": 2,
    "total_steps": 5
  }
}
```

### 구독 이벤트
- `RECORDING_STARTED` → current_task = "recording"
- `STT_RESULT_RECEIVED` → last_query 업데이트
- `LLM_COMMAND_RECEIVED` → current_site, current_task 업데이트
- `TTS_PLAYBACK_FINISHED` → current_task = "idle"

### 발행 이벤트
- `SESSION_UPDATED` - 세션 상태 변경 (data: dict)

### 환경 변수
```env
SESSION_FILE_PATH=./session.json
SESSION_AUTO_SAVE=true
```

---

## F-07: 상태 표시

### 기능 설명
최소한의 UI 창으로 현재 앱 상태 표시.

### 상세 동작
1. 앱 시작 시 상태 창 표시
2. 이벤트에 따라 상태 텍스트 업데이트
3. 항상 최상위에 표시

### 담당 모듈
- `ui/ui_manager.py` - UI 관리
- `ui/mini_window.py` - tkinter 창

### UI 상태 종류
| 상태 | 표시 텍스트 | 트리거 이벤트 |
|------|------------|--------------|
| idle | 대기 중 | `TTS_PLAYBACK_FINISHED` |
| recording | 녹음 중 | `RECORDING_STARTED` |
| processing | 처리 중 | `RECORDING_STOPPED` |
| playing | 재생 중 | `TTS_AUDIO_RECEIVED` |
| error | 오류: {msg} | `ERROR_OCCURRED` |

### 구독 이벤트
- `RECORDING_STARTED` → "녹음 중"
- `RECORDING_STOPPED` → "처리 중"
- `TTS_AUDIO_RECEIVED` → "재생 중"
- `TTS_PLAYBACK_FINISHED` → "대기 중"
- `ERROR_OCCURRED` → "오류: {message}"

### 창 사양
- 크기: 300x150 px
- 위치: 우측 하단
- 항상 위: Yes

---

## F-08: 텍스트 입력 (테스트용)

### 기능 설명
개발/디버깅 목적으로 콘솔에서 직접 텍스트를 입력하여 AI 서버로 전송. 음성 녹음 → STT 과정을 건너뛰고 바로 텍스트 명령을 테스트할 수 있음.

### 상세 동작
1. 콘솔/터미널에서 텍스트 입력 대기
2. 사용자가 텍스트 입력 후 Enter
3. 입력된 텍스트를 AI 서버로 전송 (STT 결과처럼 처리)
4. 서버 응답(TTS/MCP 명령) 수신 및 처리

### 담당 모듈
- `debug/console_input.py` - 콘솔 입력 처리

### 발행 이벤트
- `TEXT_INPUT_READY` - 텍스트 입력 완료 (data: str)

### 메시지 타입 (Client → Server)
```json
{
  "type": "text_input",
  "data": {
    "text": "쿠팡에서 우유 검색해줘"
  },
  "session_id": "uuid-v4"
}
```

### 사용 방법
```bash
# 앱 실행 시 --console 플래그로 활성화
python main.py --console
```

### 환경 변수
```env
DEBUG_CONSOLE_ENABLED=false
```

---

## 이벤트 목록

전체 이벤트 16개

| 이벤트 | 발행자 | 구독자 | 데이터 |
|--------|--------|--------|--------|
| `HOTKEY_PRESSED` | audio.hotkey | ui, audio.recorder | None |
| `RECORDING_STARTED` | audio.recorder | ui, session | None |
| `RECORDING_STOPPED` | audio.recorder | ui, session | None |
| `AUDIO_READY` | audio.recorder | network | bytes |
| `STT_RESULT_RECEIVED` | network | ui, session | str |
| `LLM_COMMAND_RECEIVED` | network | session | dict |
| `MCP_TOOL_CALL` | network | mcp.client | dict |
| `MCP_RESULT` | mcp.client | network | dict |
| `TTS_AUDIO_RECEIVED` | network | audio.player | bytes |
| `TTS_PLAYBACK_FINISHED` | audio.player | ui, session | None |
| `BROWSER_READY` | browser.launcher | mcp.server_manager | dict |
| `MCP_SERVER_READY` | mcp.server_manager | mcp.client | dict |
| `SESSION_UPDATED` | session | ui | dict |
| `ERROR_OCCURRED` | 모든 모듈 | ui, session | str/dict |
| `APP_SHUTDOWN` | main | 모든 모듈 | None |
| `TEXT_INPUT_READY` | debug.console_input | network | str |

---

## 인터페이스 정의

### Audio 모듈

```python
class IHotkeyManager:
    def start(self) -> None: ...
    def stop(self) -> None: ...

class IAudioRecorder:
    def start_recording(self) -> None: ...
    def stop_recording(self) -> bytes: ...
    def is_recording(self) -> bool: ...

class IAudioPlayer:
    def play(self, audio_data: bytes) -> None: ...
    def stop(self) -> None: ...
    def is_playing(self) -> bool: ...
```

### Browser 모듈

```python
class IBrowserController:
    def launch_chrome(self) -> bool: ...
    def close_chrome(self) -> None: ...
    def get_cdp_url(self) -> str: ...
    def is_running(self) -> bool: ...
```

### MCP 모듈

```python
class IMCPServerManager:
    async def start_server(self) -> bool: ...
    async def stop_server(self) -> None: ...
    def is_running(self) -> bool: ...

class IMCPClient:
    async def connect(self) -> bool: ...
    async def call_tool(self, tool_name: str, arguments: dict) -> dict: ...
    async def disconnect(self) -> None: ...
```

### Network 모듈

```python
class IWebSocketClient:
    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    async def send_message(self, message_type: str, data: dict) -> None: ...
    def is_connected(self) -> bool: ...
```

### Session 모듈

```python
class ISessionManager:
    def get_state(self) -> dict: ...
    def update_state(self, key: str, value: Any) -> None: ...
    def save_state(self) -> None: ...
    def load_state(self) -> dict: ...
```

### UI 모듈

```python
class IUIManager:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def update_status(self, status: str) -> None: ...
```

---

## 에러 처리

### 에러 타입

| 에러 타입 | 발생 상황 | 처리 방법 |
|-----------|----------|----------|
| ConnectionError | WebSocket/MCP/CDP 연결 실패 | 재연결 시도 |
| TimeoutError | 도구 실행/서버 응답 타임아웃 | 재시도 또는 실패 반환 |
| IOError | 마이크/스피커 접근 실패 | 에러 로그 + 사용자 알림 |
| ProcessError | Chrome/MCP 서버 실행 실패 | 재시도 또는 앱 종료 |

### 에러 이벤트 발행
```python
await publish(
    EventType.ERROR_OCCURRED,
    source="module_name",
    data={
        "module": "network.ws_client",
        "error_type": "ConnectionError",
        "message": "WebSocket connection failed"
    }
)
```

---

## 환경 변수 전체 목록

```env
# Network
WS_URL=ws://localhost:8000/ws
WS_RECONNECT_DELAY=5
WS_MAX_RETRIES=10

# Audio
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_CHUNK_SIZE=1024
HOTKEY=v

# Browser
BROWSER_EXECUTABLE_PATH=
BROWSER_CDP_PORT=9222
BROWSER_USER_DATA_DIR=./chrome_profile
BROWSER_HEADLESS=false

# MCP
MCP_SERVER_COMMAND=python mcp/playwright_mcp_server.py
MCP_SERVER_TIMEOUT=10
MCP_TOOL_TIMEOUT=60

# Session
SESSION_FILE_PATH=./session.json
SESSION_AUTO_SAVE=true

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log

# Debug
DEBUG_CONSOLE_ENABLED=false
```

---

**문서 버전**: 1.1
**작성일**: 2026-01-15
