# ASR-LLM 파이프라인 통합 가이드

> 음성 입력 → 텍스트 변환 → 명령 생성 → MCP 실행

**버전**: 1.0  
**최종 수정**: 2026-01-22

---

## 1. 개요

### 목적
시각장애인 사용자가 **음성으로 쇼핑 명령**을 내리면, AI 서버가 이를 텍스트로 변환하고 MCP 브라우저 자동화 명령으로 변환하여 실행합니다.

### 주요 기능
- **PTT (Push-to-Talk)**: 버튼을 누르고 있는 동안만 녹음
- **3초 자동 청크**: 긴 녹음은 3초마다 자동으로 서버로 전송
- **규칙 기반 + LLM Fallback**: 먼저 규칙으로 매칭 시도, 실패 시 LLM 사용
- **실시간 TTS 응답**: 명령 실행 후 음성 피드백

---

## 2. 아키텍처

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Client (MCP App / Test Script)                                          │
│                                                                          │
│  [마이크] → [SPACE 누르기] → audio_chunk 전송                            │
│                                                                          │
│  3초마다: is_final=false (버퍼 누적)                                     │
│  놓을 때: is_final=true  (transcribe 실행)                               │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  AI Server (Docker: herewego-ai)                                         │
│                                                                          │
│  WebSocket /ws                                                           │
│       │                                                                  │
│       ▼                                                                  │
│  audio_chunk 수신 → Audio Queue → ASR Worker                            │
│                                      │                                   │
│                    [is_final=true] ──┼──→ Faster-Whisper (GPU)          │
│                                      │                                   │
│                                      ▼                                   │
│                               asr_result 전송                            │
│                                      │                                   │
│                                      ▼                                   │
│                          _process_text_input()                           │
│                                      │                                   │
│                    ┌─────────────────┼─────────────────┐                 │
│                    ▼                 ▼                 ▼                 │
│               NLU (선택)      LLMPlanner           Flow Engine           │
│                                      │                                   │
│                    ┌─────────────────┼─────────────────┐                 │
│                    ▼                                   ▼                 │
│            CommandGenerator                     LLMGenerator             │
│            (규칙 기반)                          (OpenAI fallback)        │
│                    │                                   │                 │
│                    └───────────────┬───────────────────┘                 │
│                                    ▼                                     │
│                            tool_calls 전송                               │
│                                    │                                     │
│                                    ▼                                     │
│                            TTS 응답 전송                                 │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  MCP 앱 (브라우저 자동화)                                                 │
│                                                                          │
│  tool_calls 수신 → 명령 실행 → mcp_result 전송                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 메시지 흐름

### 3.1 클라이언트 → 서버

| 메시지 타입 | 설명 | 필드 |
|------------|------|------|
| `audio_chunk` | 오디오 청크 전송 | `audio`, `seq`, `is_final` |
| `user_input` | 텍스트 직접 입력 | `text` |

### 3.2 서버 → 클라이언트

| 메시지 타입 | 설명 | 필드 |
|------------|------|------|
| `asr_result` | ASR 변환 결과 | `text`, `confidence`, `is_final` |
| `tool_calls` | LLM 생성 명령 | `commands[]` |
| `tts_chunk` | TTS 응답 | `audio`, `is_final` |
| `error` | 에러 | `error` |

---

## 4. 테스트 방법

### 4.1 필수 환경
```bash
# Python 3.11 + 필수 패키지
pip install pyaudio websockets keyboard
```

### 4.2 Docker 서버 실행
```bash
# AI 디렉토리에서
cd AI
docker-compose up -d

# 서버 로그 확인
docker logs herewego-ai --tail 20
```

### 4.3 PTT 테스트 실행
```bash
cd AI
py -3.11 tests/test_ws_ptt.py --host localhost --port 8000
```

### 4.4 테스트 사용법
1. **SPACE 누르고 있기** → 녹음 시작
2. 음성 명령 (예: "쿠팡에서 우유 검색해줘")
3. **SPACE 놓기** → 녹음 종료 및 전송
4. **ESC** → 종료

### 4.5 예상 출력
```
[REC] Recording started...
[SEND] PARTIAL chunk #1 (2.69s, 86016 bytes)    ← 3초마다 자동 전송
[STOP] Recording stopped (1.15s)
[SEND] FINAL chunk #2 (1.15s, 36864 bytes)      ← 스페이스바 놓으면 전송

[FINAL] 쿠팡에서 우유 검색해줘 (conf=1.00)      ← ASR 결과

[LLM] 명령 5개 생성:                            ← LLM 명령 생성
  [1] goto: {'url': 'https://www.coupang.com/'}
  [2] fill: {'selector': 'input[name="q"]', 'text': '우유'}
  [3] click: {'selector': 'button.headerSearchBtn'}
  ...

[TTS] 응답 완료                                 ← TTS 응답
```

---

## 5. 관련 파일

| 파일 | 역할 |
|------|------|
| `api/websocket.py` | WebSocket 핸들러, 파이프라인 오케스트레이션 |
| `services/asr/service.py` | Faster-Whisper 기반 ASR |
| `services/llm/service.py` | LLMPlanner (규칙 + LLM) |
| `services/llm/command_generator.py` | 규칙 기반 명령 생성 |
| `services/llm/llm_generator.py` | OpenAI 기반 LLM fallback |
| `services/llm/rules/` | 개별 규칙 모듈 |
| `core/interfaces.py` | 데이터 클래스 정의 |
| `tests/test_ws_ptt.py` | PTT 테스트 스크립트 |

---

## 6. 트러블슈팅

### 6.1 `[ERROR] Processing error`
- **원인**: 세션 또는 속성 누락
- **확인**: `docker logs herewego-ai --tail 50`

### 6.2 `[FINAL]`만 나오고 `[LLM]` 없음
- **원인**: 세션 ID 불일치
- **확인**: 서버 로그에서 session ID 확인

### 6.3 ASR 결과가 이상함
- **원인**: 마이크 음질 또는 환경 소음
- **해결**: 다른 마이크 사용 (`--device N`)

---

## 7. 참고 문서

- [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md) - 메시지 프로토콜 상세
- [WEBSOCKET_STREAMING_ARCHITECTURE.md](./WEBSOCKET_STREAMING_ARCHITECTURE.md) - ASR 스트리밍 아키텍처
