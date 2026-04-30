# ASR → LLM → MCP 통합 파이프라인

> 음성 명령 → AI 처리 → 브라우저 자동화

**버전**: 1.0  
**최종 검증**: 2026-01-22

---

## 1. 개요

시각장애인을 위한 음성 기반 웹 쇼핑 지원 시스템입니다. 사용자의 음성 명령을 AI가 처리하여 브라우저를 자동으로 제어합니다.

### 시스템 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  사용자: "쿠팡에서 우유 검색해줘"                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PTT 스크립트 (임시) / MCP 앱 (향후)                              │
│  - SPACE 키로 녹음 시작/종료                                      │
│  - 오디오 청크를 AI 서버로 WebSocket 전송                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  AI 서버 (Docker: herewego-ai)                                   │
│                                                                 │
│  1. ASR (Faster-Whisper)                                        │
│     오디오 → 텍스트: "쿠팡에서 우유 검색해줘"                       │
│                                                                 │
│  2. LLM (OpenAI/GMS)                                            │
│     텍스트 → MCP 명령:                                           │
│     - goto: "https://www.coupang.com"                           │
│     - fill: 검색창에 "우유" 입력                                  │
│     - click: 검색 버튼 클릭                                       │
│                                                                 │
│  3. WebSocket broadcast (tool_calls)                            │
│     명령을 모든 클라이언트에 전송                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  MCP 앱 (Desktop)                                               │
│                                                                 │
│  1. WSClient: tool_calls 수신                                    │
│  2. MCPHandler: 명령 실행                                        │
│  3. BrowserTools (Playwright): 실제 브라우저 제어                 │
│  4. mcp_result 응답 전송                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Chrome 브라우저                                                 │
│  - 쿠팡 페이지 열림                                              │
│  - 검색창에 "우유" 입력                                          │
│  - 검색 결과 표시                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 빠른 시작

### 2.1 사전 요구사항

- Docker & Docker Compose
- Python 3.11+ (AI 서버 테스트용)
- Python 3.13+ (MCP 앱용, venv 포함)
- Chrome 브라우저

### 2.2 실행 순서

```bash
# 터미널 1: AI 서버
cd AI
docker-compose up -d
docker logs herewego-ai --tail 20  # 시작 확인

# 터미널 2: MCP 앱
cd MCP
source venv/Scripts/activate  # Windows: venv\Scripts\activate
python main.py

# 터미널 3: PTT 테스트 (임시)
cd AI
py -3.11 tests/test_ws_ptt.py
```

### 2.3 음성 입력

1. PTT 스크립트에서 **SPACE 키를 누른 상태**로 말하기
2. SPACE 키를 **놓으면** 전송
3. Chrome이 자동으로 동작

---

## 3. 아키텍처

### 3.1 컴포넌트 구성

```
S14P11D108/
├── AI/                          # AI 서버 (Docker)
│   ├── api/
│   │   └── websocket.py         # WebSocket 핸들러
│   ├── services/
│   │   ├── asr/service.py       # Faster-Whisper ASR
│   │   ├── llm/service.py       # LLM Planner
│   │   └── tts/service.py       # TTS 서비스
│   └── tests/
│       └── test_ws_ptt.py       # PTT 테스트 스크립트
│
└── MCP/                         # MCP 데스크탑 앱
    ├── browser/
    │   └── launcher.py          # Chrome 자동 실행
    ├── mcp/
    │   ├── handler.py           # MCP 도구 핸들러
    │   └── tools.py             # BrowserTools (Playwright)
    ├── network/
    │   └── ws_client.py         # AI 서버 WebSocket 클라이언트
    └── core/
        ├── event_bus.py         # 이벤트 버스
        └── config.py            # 설정 관리
```

### 3.2 메시지 프로토콜

| 방향 | 메시지 타입 | 설명 |
|------|------------|------|
| PTT → AI | `audio_chunk` | 오디오 데이터 (바이너리) |
| AI → All | `asr_result` | ASR 결과 텍스트 |
| AI → All | `tool_calls` | MCP 명령 목록 (**브로드캐스트**) |
| AI → All | `tts_chunk` | TTS 오디오 응답 |
| MCP → AI | `mcp_result` | 도구 실행 결과 |

### 3.3 지원 도구 (MCP Tools)

| 도구 | 설명 | 인자 |
|------|------|------|
| `goto` | URL 이동 | `url` |
| `click` | 요소 클릭 | `selector` |
| `fill` | 텍스트 입력 | `selector`, `text` |
| `press_key` | 키 입력 | `key` |
| `scroll` | 스크롤 | `direction`, `amount` |
| `wait` | 대기 | `ms` |

---

## 4. 설정

### 4.1 MCP 앱 설정 (`.env`)

```bash
# WebSocket 서버
WS_URL=ws://localhost:8000/ws

# Chrome 설정
BROWSER_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
BROWSER_CDP_PORT=9222
BROWSER_USER_DATA_DIR=.mcp_chrome_profile

# 디버그
DEBUG_CONSOLE_ENABLED=true
```

### 4.2 AI 서버 설정

Docker Compose에서 자동 설정됨. 환경변수:
- `OPENAI_API_KEY` 또는 `GMS_API_KEY`

---

## 5. 주요 로그

### 성공 시 예상 로그

**MCP 앱:**
```
browser.launcher - INFO - Found existing Chrome CDP at port 9222
browser.launcher - INFO - Connected to existing Chrome - CDP URL: ws://...
network.ws_client - INFO - Connected to AI server: ws://localhost:8000/ws/...
mcp.handler - INFO - MCP handler is ready
network.ws_client - INFO - Received 5 tool call(s)
mcp.tools - INFO - Executing tool: goto
```

**PTT 스크립트:**
```
[REC] Recording started...
[SEND] FINAL chunk #2 (1.47s, 47104 bytes)
[FINAL] 쿠팡에서 우유 검색해줘 (conf=1.00)
[LLM] 명령 5개 생성:
  [1] goto: {'url': 'https://www.coupang.com/'}
```

---

## 6. 알려진 제한사항

### 현재 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| ASR → LLM | ✅ 완료 | PTT 스크립트로 테스트 |
| LLM → MCP | ✅ 완료 | 브로드캐스트 방식 |
| MCP → Browser | ✅ 완료 | Playwright CDP |
| MCP 오디오 통합 | ⏳ 예정 | 단일 앱 통합 필요 |
| 세션 관리 | ⏳ 예정 | 브로드캐스트 → 세션 기반 |

### 개선 필요 사항

1. **MCP 앱에 오디오 입력 통합**: 현재 별도 PTT 스크립트 사용
2. **세션 기반 통신**: 현재 브로드캐스트 방식 (임시)
3. **Chrome 프로필 관리**: 프로필 디렉토리 충돌 해결 필요

---

## 7. 트러블슈팅

### 7.1 Chrome 프로필 에러

**증상:** "데이터 디렉터리를 읽고 쓸 수 없습니다"

**해결:**
```bash
# 기존 프로필 삭제
rm -rf .mcp_chrome_profile chrome_profile chrome_mcp_profile

# MCP 앱 재시작
python main.py
```

### 7.2 WebSocket 연결 실패

**증상:** "Failed to connect to AI server"

**해결:**
```bash
# Docker 상태 확인
docker ps
docker logs herewego-ai --tail 20

# 필요시 재시작
docker-compose down && docker-compose up -d
```

### 7.3 CDP 연결 타임아웃

**증상:** "Failed to get CDP URL"

**해결:** Chrome 수동 실행
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome_cdp_profile"
```

---

## 8. 참고 문서

- [ASR_LLM_PIPELINE.md](./ASR_LLM_PIPELINE.md) - 음성 인식 및 LLM 처리 상세
- [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) - WebSocket 메시지 형식
- [MCP/README.md](../MCP/README.md) - MCP 앱 설명
