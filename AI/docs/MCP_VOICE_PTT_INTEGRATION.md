# MCP Voice PTT 통합

본 문서는 처음 합류하는 개발자도 맥락을 이해할 수 있도록 비즈니스 문서 형식으로 작성되었습니다.

## 개요
- **프로젝트**: MCP Desktop App - 음성 기반 웹 쇼핑 보조
- **수정 파일**: `MCP/audio/audio_manager.py` (신규), `MCP/network/ws_client.py`, `MCP/main.py`, `MCP/browser/launcher.py`, `MCP/requirements.txt`
- **일시**: 2026-01-23
- **버전**: v1.0.0
- **Phase**: Phase 2 - Voice Input Integration
- **의도**: 시각장애인 사용자가 음성으로 웹 쇼핑을 제어할 수 있도록 PTT(Push-to-Talk) 기능 통합
- **동작**: SPACE 키를 누르면 녹음 시작, 놓으면 AI 서버로 전송 → ASR → LLM → MCP 명령 실행

## 아키텍처 / 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Desktop App                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    AUDIO_READY     ┌──────────────┐              │
│  │ AudioManager │ ──────────────────▶│   WSClient   │              │
│  │  (SPACE키)   │    EventBus        │              │              │
│  └──────────────┘                    └──────┬───────┘              │
│         │                                    │                      │
│         │ RECORDING_STARTED                  │ audio_chunk         │
│         │ RECORDING_STOPPED                  │ (WebSocket)         │
│         ▼                                    ▼                      │
│  ┌──────────────┐              ┌─────────────────────────┐         │
│  │  UIManager   │              │      AI Server          │         │
│  │ (상태 표시)   │              │  ┌─────┐  ┌─────────┐  │         │
│  └──────────────┘              │  │ ASR │─▶│LLMPlanner│  │         │
│                                │  └─────┘  └────┬────┘  │         │
│  ┌──────────────┐              │                │       │         │
│  │  MCPHandler  │◀─────────────│  tool_calls ◀──┘       │         │
│  │ (브라우저제어)│  (WebSocket)  └─────────────────────────┘         │
│  └──────┬───────┘                                                  │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────┐                                                  │
│  │   Chrome     │  CDP (DevTools Protocol)                         │
│  │  (자동화)     │                                                   │
│  └──────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 메시지 흐름

1. **사용자**: SPACE 키 누르기 (녹음 시작)
2. **AudioManager**: 마이크 녹음, 3초마다 `audio_chunk(is_final=false)` 전송
3. **사용자**: SPACE 키 놓기 (녹음 종료)
4. **AudioManager**: 최종 `audio_chunk(is_final=true)` 전송
5. **AI Server (ASR)**: 음성 → 텍스트 변환 (Faster-Whisper)
6. **AI Server (LLM)**: 텍스트 → MCP 명령 생성
7. **WSClient**: `tool_calls` 수신
8. **MCPHandler**: Chrome 브라우저에서 명령 실행

### 오디오 스펙

| 항목 | 값 |
|------|-----|
| Sample Rate | 16kHz |
| Channels | Mono (1) |
| Bit Depth | 16-bit |
| Format | RAW PCM → Base64 |
| Chunk Interval | 3초 |

## 검증

### 테스트 시나리오

```bash
# 1. AI 서버 실행 확인
docker ps  # herewego-ai 컨테이너 확인

# 2. MCP 앱 실행
cd MCP
source venv/Scripts/activate  # Windows
python main.py

# 3. PTT 테스트
# - SPACE 키 누르고 "쿠팡에서 삼겹살 검색해줘" 말하기
# - SPACE 키 놓기
# - Chrome에서 쿠팡 검색 결과 확인
```

### 성공 로그 예시

```
INFO - Recording started
INFO - Sending PARTIAL chunk #1 (2.62s, 83968 bytes)
INFO - Recording stopped (1.60s)
INFO - Sending FINAL chunk #2 (1.60s, 51200 bytes)
INFO - ASR result: 쿠팡에서 삼겹살 검색해줘
INFO - Received 5 tool call(s)
INFO -   [1] goto: 쿠팡 이동
INFO -   [2] wait: 페이지 로딩 대기
INFO -   [3] fill: '삼겹살' 입력
INFO -   [4] click: 검색 버튼 클릭
INFO -   [5] wait: 검색 결과 로딩 대기
INFO - Navigated to: https://www.coupang.com/
INFO - Filled input input[name="q"] with: 삼겹살
INFO - Clicked element: button.headerSearchBtn
```

---

## 트러블슈팅

### 1. WebSocket 연결 끊김 (False Positive)

**원인**: `websocket.closed` 속성이 비동기 환경에서 잘못된 값을 반환하여, 연결이 실제로 유지되는데도 "Not connected"로 판단

**해결**: `is_connected` 속성을 단순화하고 실제 전송 시 예외 처리로 대응
```python
# Before
return not self._websocket.closed  # 불안정

# After
return self._websocket is not None  # 단순화
```

**검증**: 연속적인 음성 명령 성공 확인

---

### 2. Chrome 프로필 디렉토리 권한 문제

**원인**: 상대 경로 `.mcp_chrome_profile`을 Chrome이 잘못 해석, 또는 이전 실행에서 프로필 잠금

**해결**: 
1. `Path.resolve()`로 절대 경로 변환
2. 잠긴 프로필 감지 시 `_1`, `_2` 등 번호 붙여서 대체 프로필 사용

```python
base_user_data_dir = Path(self._config.user_data_dir).resolve()
user_data_dir = await self._find_available_profile_dir(base_user_data_dir)
```

**로그**:
```
INFO - Profile directory is locked: ...\.mcp_chrome_profile
INFO - Using alternative profile: ...\.mcp_chrome_profile_1
```

**검증**: 프로필 잠금 후에도 앱 정상 시작

---

### 3. 수동 브라우저 조작 후 명령 실패

**원인**: 사용자가 수동으로 브라우저를 조작하면 CDP 페이지 컨텍스트가 변경됨

**해결**: 현재 제한사항으로 문서화. 시각장애인 사용 시나리오에서는 음성으로만 조작하므로 문제되지 않음

**로그**:
```
ERROR - Navigation failed: Page.goto: Target page, context or browser has been closed
```

---

## 레퍼런스

- [ASR_LLM_PIPELINE.md](./ASR_LLM_PIPELINE.md) - AI 서버 파이프라인 문서
- [AI/tests/test_ws_ptt.py](../tests/test_ws_ptt.py) - PTT 테스트 스크립트 참조
- [AI/api/websocket.py](../api/websocket.py) - AI 서버 WebSocket 핸들러

---

## 익명화 확인

| 항목 | 상태 |
|------|------|
| 도메인 | ✅ localhost, coupang.com (공개) |
| IP/포트 | ✅ 127.0.0.1:9222, 8000 (로컬) |
| 인증정보 | ✅ 없음 |
| DB접속정보 | ✅ 없음 |
| 레포URL | ✅ 익명화됨 |
| 커밋author | ✅ 익명화됨 |
| 서버명 | ✅ herewego-ai (가명) |
| 경로 내 사용자명 | ✅ 문서에서 제외 |
| 로그 내 민감정보 | ✅ 없음 |
