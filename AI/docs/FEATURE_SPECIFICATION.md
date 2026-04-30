# AI 서버 기능 명세서

> 시각장애인 음성 쇼핑 지원을 위한 AI 서버 기능 목록 및 상세 정의

---

## 핵심 기능 목록

| 번호 | 카테고리 | 기능명 | 설명 | 담당자 |
|------|---------|--------|------|--------|
| AI-01 | ASR | WebSocket 오디오 수신 | 로컬의 audio_chunk 수신 및 파싱 | 김민찬 |
| AI-02 | ASR | 실시간 STT 처리 | Faster-Whisper(turbo)로 실시간 ASR 처리(청크 단위) | 김민찬 |
| AI-03 | ASR | STT 결과 반환 | STT 결과를 stt_result로 스트리밍 반환 | 김민찬 |
| AI-04 | LLM | 의도 분석 | Intent 검색/비교/장바구니/결제 등 분류 | 김재환 |
| AI-05 | LLM | MCP 명령 생성 | 텍스트 → Playwright MCP의 브라우저 실행용 tool_calls 생성 | 김재환 |
| AI-06 | LLM | 플로우 엔진 | 쇼핑몰별 회원가입/결제 같은 복잡한 작업을 순환하기 위해 플로우(step) 생성 | 김재환 |
| AI-07 | LLM | 대화형 응답 생성 | 실질 결제 기반 다음 절차/작업 멘트 생성(대화형) | 김재환 |
| AI-08 | LLM | 플로우 위임 판단 | 일반 명령 vs 회원가입/결제 플로우 위임 판단 | 김재환 |
| AI-09 | OCR | 결제 영역 인식 | CAPTCHA/키패드 영역 검출 같이 결제 영역에서의 수치 배열 자동 | 하주형 |
| AI-10 | OCR | 상품 이미지 인식 | 상품 이미지에서 텍스트/시각 특징 추출(색/형태/브랜드 라벨) | 하주형 |
| AI-11 | TTS | 음성 합성 | 텍스트 → 음성 생성(TTS) 후 tts_chunk로 스트리밍 전송 | 김민찬 |
| AI-12 | TTS | 상품 정보 요약 | 상품 정보 핵심 요약 안내(카테고리별 별도 전략) | 김민찬 |

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

## AI-01: 음성 인식 (STT)

### 기능 설명
사용자 음성을 실시간 스트리밍으로 텍스트로 변환.

### 상세 동작
1. MCP 앱에서 오디오 청크 수신 (WebSocket)
2. Faster-Whisper(turbo) 모델로 한국어 음성 인식
3. STT 결과 텍스트를 MCP 앱으로 전송

### 담당 모듈
- `services/stt.py` - Whisper 모델 로딩, 스트리밍 STT

### 환경 변수
```env
STT_MODEL=faster-whisper-turbo
STT_LANGUAGE=ko
STT_DEVICE=cuda
```

---

## AI-02: 음성 합성 (TTS)

### 기능 설명
AI 응답 텍스트를 자연스러운 한국어 음성으로 변환.

### 상세 동작
1. LLM 응답 텍스트 수신
2. Hugging Face TTS 모델로 음성 합성
3. 음성 청크를 실시간 스트리밍으로 MCP 앱에 전송

### 담당 모듈
- `services/tts.py` - HF TTS 모델, 음성 합성

### TTS 모델 후보
| 모델 | 지연시간 | 한국어 | 비고 |
|------|----------|--------|------|
| ElevenLabs Flash v2.5 | ~75ms | O | 실시간 에이전트 최적화 |
| MiniMax Speech-02-HD | - | O | 아시아 언어 특화, 저렴 |
| CosyVoice 2.0 | 150ms | O | 무료 (오픈소스) |

### 환경 변수
```env
TTS_PROVIDER=minimax
TTS_VOICE_ID=korean_female_1
```

---

## AI-03: WebSocket 통신

### 기능 설명
MCP 앱과 실시간 양방향 스트리밍 통신.

### 상세 동작
1. MCP 앱 WebSocket 연결 수립
2. 오디오 청크 수신 → STT 처리
3. LLM 명령/TTS 음성 → MCP 앱 전송
4. 연결 끊김 시 재연결 처리

### 담당 모듈
- `websocket/gateway.py` - WebSocket 연결 관리
- `websocket/handlers.py` - 메시지 타입별 처리

### 메시지 타입
| 방향 | 타입 | 설명 |
|------|------|------|
| 로컬 → 서버 | `audio_chunk` | 녹음 중인 음성 청크 |
| 서버 → 로컬 | `stt_result` | STT 변환 텍스트 |
| 서버 → 로컬 | `tool_calls` | LLM 생성 MCP 명령 |
| 서버 → 로컬 | `tts_chunk` | TTS 음성 청크 |
| 서버 → 로컬 | `flow_step` | 플로우 단계 정보 |

### 환경 변수
```env
WS_MAX_CONNECTIONS=100
WS_HEARTBEAT_INTERVAL=30
```

---

## AI-04: 세션 관리

### 기능 설명
쇼핑 세션 동안 대화 맥락과 상태를 유지.

### 상세 동작
1. WebSocket 연결 시 세션 생성
2. 현재 사이트, 진행 중 플로우, 검색 기록 저장
3. "아까 그 상품" 등 대명사 참조 해석
4. 연결 종료 시 세션 정리

### 담당 모듈
- `websocket/session.py` - 세션 생성/관리/삭제

### 세션 데이터 구조
```python
{
    "session_id": "uuid-v4",
    "current_site": "coupang",
    "current_task": "searching",
    "last_query": "무선 이어폰",
    "search_results": [...],
    "flow": {
        "flow_id": "coupang_checkout",
        "current_step": 2
    }
}
```

### 환경 변수
```env
SESSION_BACKEND=memory  # memory | redis
REDIS_URL=redis://localhost:6379
SESSION_TTL=3600
```

---

## AI-05: LLM 명령 생성

### 기능 설명
사용자 자연어를 MCP 브라우저 명령으로 변환.

### 상세 동작
1. STT 결과 텍스트 수신
2. GPT-5-mini로 의도 분석 및 명령 생성
3. MCP tool_call 형식으로 변환하여 전송

### 담당 모듈
- `services/llm.py` - OpenAI API, 명령 생성

### 예시 변환
```
입력: "쿠팡에서 물티슈 검색해줘"

출력:
{
    "tool_name": "navigate_to_url",
    "arguments": {"url": "https://www.coupang.com"}
}
→
{
    "tool_name": "fill_input",
    "arguments": {"selector": "#searchKeyword", "value": "물티슈"}
}
→
{
    "tool_name": "click_element",
    "arguments": {"selector": "#searchBtn"}
}
```

### 환경 변수
```env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-5-mini
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.7
```

---

## AI-06: 플로우 엔진

### 기능 설명
회원가입/결제 등 복잡한 작업을 단계별로 처리.

### 상세 동작
1. LLM이 플로우 필요 여부 판단
2. 사이트별 플로우 JSON 로딩
3. 각 단계 실행 → 사용자 확인 → 다음 단계
4. 결제 전 최종 확인 삽입 (Policy/Guard)

### 담당 모듈
- `services/flow_engine.py` - 플로우 상태 머신
- `flows/` - 사이트별 플로우 JSON

### 플로우 단계 구조
```python
{
    "flow_type": "checkout",
    "site": "coupang",
    "steps": [
        {
            "prompt": "배송지를 확인해주세요. 서울시 강남구...",
            "required_fields": ["address"],
            "action": {"tool_name": "click_element", "arguments": {...}},
            "validation": "success_selector",
            "fallback": "배송지 확인에 실패했습니다"
        }
    ]
}
```

### 지원 플로우
| 사이트 | 검색 | 결제 | 회원가입 |
|--------|------|------|----------|
| 쿠팡 | O | O | O |
| 네이버쇼핑 | O | O | - |
| 11번가 | O | O | - |

---

## AI-07: OCR 인식

### 기능 설명
결제 키패드, CAPTCHA 등 인증 이미지 인식.

### 상세 동작
1. MCP 앱에서 스크린샷 수신
2. TrOCR/PaddleOCR로 이미지 텍스트 추출
3. 키패드 영역 검출 → 숫자 매핑
4. 인식 결과를 LLM에 전달

### 담당 모듈
- `services/ocr.py` - HF OCR 모델, 키패드 인식

### 환경 변수
```env
OCR_MODEL=trocr-base-printed
OCR_DEVICE=cuda
```

---

## AI-08: WebRTC 시그널링

### 기능 설명
보호자가 원격으로 사용자 화면을 모니터링/제어.

### 상세 동작
1. 보호자 앱에서 WebRTC 연결 요청
2. 시그널링 서버로 오퍼/앤서 교환
3. ICE 후보 교환으로 P2P 연결 수립
4. 보호자 세션 관리

### 담당 모듈
- `webrtc/signaling.py` - WebRTC 오퍼/앤서
- `webrtc/guardian.py` - 보호자 세션 관리

---

## AI-09: HTTP API

### 기능 설명
인증, 헬스체크, 백엔드 통신을 위한 REST API.

### 담당 모듈
- `api/health.py` - /health, /status
- `api/auth.py` - /auth/token, 토큰 관리
- `api/backend.py` - /backend/cart, /backend/order

### 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /health | 서버 상태 확인 |
| POST | /auth/token | 토큰 발급 |
| POST | /auth/refresh | 토큰 갱신 |
| POST | /backend/cart | 장바구니 조회 |

---

## AI-10: 시스템 통합

### 기능 설명
모든 모듈을 FastAPI 앱으로 통합 및 배포.

### 담당 모듈
- `main.py` - FastAPI 앱 초기화, 라우터 등록
- `core/config.py` - 환경 변수 관리
- `core/logging.py` - 로깅 설정

### 시스템 아키텍처
```
┌─────────────────────────────────────────────────────────────┐
│                        AI Server                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  API Service │    │   WebSocket  │    │   Session    │   │
│  │    (HTTP)    │    │   Gateway    │    │   Manager    │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         ┌────────────────────┼────────────────────┐         │
│         ▼                    ▼                    ▼         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ ASR Service  │    │ LLM Planner  │    │ TTS Service  │   │
│  │(Whisper)     │    │ (GPT-5-mini) │    │(HF TTS)      │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                              │                              │
│                              ▼                              │
│                      ┌──────────────┐                       │
│                      │ Flow Engine  │                       │
│                      └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 환경 변수 전체 목록

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# STT
STT_MODEL=faster-whisper-turbo
STT_LANGUAGE=ko
STT_DEVICE=cuda

# TTS
TTS_PROVIDER=minimax
TTS_VOICE_ID=korean_female_1

# LLM
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-5-mini
LLM_MAX_TOKENS=1024

# OCR
OCR_MODEL=trocr-base-printed
OCR_DEVICE=cuda

# Session
SESSION_BACKEND=memory
REDIS_URL=redis://localhost:6379

# WebSocket
WS_MAX_CONNECTIONS=100
WS_HEARTBEAT_INTERVAL=30

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log
```

---

**문서 버전**: 1.0
**작성일**: 2026-01-16
