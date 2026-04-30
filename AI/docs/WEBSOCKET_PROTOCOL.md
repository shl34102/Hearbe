# WebSocket 프로토콜 명세서

> MCP 앱 ↔ AI 서버 간 실시간 통신 프로토콜 정의

## 개요

WebSocket을 통해 **양방향 실시간 통신**을 수행합니다.
- MCP 앱에서 오디오 스트림 전송
- AI 서버에서 ASR 결과, LLM 명령, TTS 음성 전송

## 연결 URL

```
ws://서버주소:8000/ws
```

### 헤더 (선택)
```http
Authorization: Bearer <임시_토큰>
```

---

## 메시지 포맷

모든 메시지는 **JSON** 형식입니다.

### 기본 구조
```json
{
  "type": "메시지_타입",
  "data": { ... },
  "timestamp": "2026-01-14T12:34:56Z",
  "session_id": "uuid-v4"
}
```

---

## 메시지 타입 정의

### 1. 클라이언트 → 서버

#### 1.1 `audio_chunk` - 오디오 스트림 전송 (PTT Mode)

**설명**: Push-to-Talk 방식으로 녹음한 오디오 데이터 청크 전송

**데이터 구조**:
```json
{
  "type": "audio_chunk",
  "data": {
    "audio": "base64_encoded_audio_data",
    "sample_rate": 16000,
    "channels": 1,
    "format": "pcm16",
    "seq": 123,
    "is_final": false
  },
  "timestamp": "2026-01-14T12:34:56.123Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `audio`: Base64 인코딩된 오디오 바이너리 (빈 문자열 가능)
- `sample_rate`: 샘플링 레이트 (Hz), 16000 고정
- `channels`: 채널 수, 1 (모노) 고정
- `format`: 오디오 포맷, `pcm16` 고정
- `seq`: 청크 순서 번호
- `is_final`: **녹음 종료 여부** (PTT 핵심 필드)

**PTT `is_final` 동작**:
| is_final | 상황 | 서버 동작 |
|----------|------|----------|
| `false` | 녹음 중 (3초마다 자동 전송) | 버퍼에 누적만 |
| `true` | 녹음 종료 (버튼 놓음) | 버퍼 transcribe 후 결과 전송 |

**빈 오디오 + is_final=true**:
녹음이 너무 짧을 경우 (< 0.5초), 오디오 없이 신호만 전송:
```json
{
  "type": "audio_chunk",
  "data": {
    "audio": "",
    "seq": 5,
    "is_final": true
  }
}
```

---

#### 1.2 `command` - 사용자 명령 전송

**설명**: 텍스트로 직접 명령 전송 (ASR 우회)

**데이터 구조**:
```json
{
  "type": "command",
  "data": {
    "text": "쿠팡에서 우유 검색해줘"
  },
  "timestamp": "2026-01-14T12:34:56Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### 1.3 `mcp_result` - MCP 도구 실행 결과

**설명**: MCP 앱에서 브라우저 자동화 결과를 서버로 전송

**데이터 구조**:
```json
{
  "type": "mcp_result",
  "data": {
    "request_id": "req_12345",
    "success": true,
    "result": {
      "action": "navigate",
      "url": "https://www.coupang.com",
      "status": "completed"
    },
    "error": null
  },
  "timestamp": "2026-01-14T12:34:57Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `request_id`: 서버가 보낸 `tool_call`의 ID와 매칭
- `success`: 성공 여부
- `result`: 실행 결과 데이터
- `error`: 실패 시 에러 메시지

---

#### 1.4 `user_input` - 사용자 추가 입력

**설명**: 플로우 중간에 서버가 요청한 정보 제공 (예: 주소, 전화번호)

**데이터 구조**:
```json
{
  "type": "user_input",
  "data": {
    "flow_id": "flow_67890",
    "step": "address_input",
    "value": "서울시 강남구 테헤란로 123"
  },
  "timestamp": "2026-01-14T12:35:00Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### 1.5 `heartbeat` - 연결 유지

**설명**: 주기적으로 전송하여 연결 유지 (30초마다)

**데이터 구조**:
```json
{
  "type": "heartbeat",
  "data": {},
  "timestamp": "2026-01-14T12:35:30Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 2. 서버 → 클라이언트

#### 2.1 `asr_result` - ASR 변환 결과

**설명**: 음성→텍스트 변환 결과 (실시간 스트리밍)

**데이터 구조**:
```json
{
  "type": "asr_result",
  "data": {
    "text": "쿠팡에서 우유 검색해줘",
    "confidence": 0.95,
    "language": "ko",
    "duration": 2.5,
    "is_final": true,
    "segment_id": "seg_1"
  },
  "timestamp": "2026-01-14T12:34:58Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `text`: 인식된 텍스트
- `confidence`: 신뢰도 (0.0 ~ 1.0)
- `language`: 감지된 언어 코드
- `duration`: 오디오 길이 (초)
- `is_final`: 최종 결과 여부 (false=중간 결과)
- `segment_id`: 세그먼트 식별자

---

#### 2.2 `llm_command` - LLM 명령 생성 결과

**설명**: LLM이 사용자 의도를 분석하여 생성한 명령

**데이터 구조**:
```json
{
  "type": "llm_command",
  "data": {
    "intent": "search_product",
    "site": "coupang",
    "parameters": {
      "keyword": "우유",
      "filters": {
        "rocket_delivery": true
      }
    },
    "flow_type": "search"
  },
  "timestamp": "2026-01-14T12:34:59Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `intent`: 사용자 의도 (`search_product`, `add_to_cart`, `checkout`, `signup`)
- `site`: 대상 쇼핑몰 (`coupang`, `naver`, `elevenst`)
- `parameters`: 명령 파라미터
- `flow_type`: 플로우 타입 (`search`, `checkout`, `signup`)

---

#### 2.3 `tool_call` - MCP 도구 호출 요청

**설명**: 브라우저 자동화 도구 실행 요청

**데이터 구조**:
```json
{
  "type": "tool_call",
  "data": {
    "request_id": "req_12345",
    "tool_name": "navigate_to_url",
    "arguments": {
      "url": "https://www.coupang.com"
    },
    "timeout": 30
  },
  "timestamp": "2026-01-14T12:35:00Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `request_id`: 고유 요청 ID (클라이언트가 결과 전송 시 사용)
- `tool_name`: 도구 이름 (`navigate_to_url`, `click_element`, `fill_input`, `get_text`)
- `arguments`: 도구별 파라미터
- `timeout`: 최대 실행 시간 (초)

**주요 도구 목록**:
- `navigate_to_url`: URL 이동
- `click_element`: 요소 클릭
- `fill_input`: 입력 필드 채우기
- `get_text`: 텍스트 추출
- `screenshot`: 스크린샷 캡처

---

#### 2.4 `tts_audio` - TTS 음성 데이터

**설명**: 텍스트→음성 변환 결과

**데이터 구조**:
```json
{
  "type": "tts_audio",
  "data": {
    "audio": "base64_encoded_audio_data",
    "text": "쿠팡에서 검색 결과를 찾았습니다.",
    "format": "mp3",
    "duration": 3.5
  },
  "timestamp": "2026-01-14T12:35:02Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `audio`: Base64 인코딩된 음성 바이너리
- `text`: 원본 텍스트
- `format`: 오디오 포맷 (`mp3`, `wav`)
- `duration`: 재생 시간 (초)

---

#### 2.5 `flow_step` - 플로우 단계 안내

**설명**: 회원가입/결제 플로우 진행 중 단계별 안내

**데이터 구조**:
```json
{
  "type": "flow_step",
  "data": {
    "flow_id": "flow_67890",
    "flow_type": "checkout",
    "current_step": 2,
    "total_steps": 5,
    "step_name": "address_input",
    "prompt": "배송지 주소를 말씀해주세요.",
    "required_fields": ["address", "phone"],
    "actions": [
      {
        "type": "tts",
        "text": "배송지 주소를 말씀해주세요."
      }
    ]
  },
  "timestamp": "2026-01-14T12:35:03Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 설명**:
- `flow_id`: 플로우 고유 ID
- `current_step`: 현재 단계 번호
- `total_steps`: 전체 단계 수
- `step_name`: 단계 이름
- `prompt`: TTS로 안내할 문구
- `required_fields`: 필요한 입력 필드
- `actions`: 실행할 액션 리스트

---

#### 2.6 `status` - 상태 업데이트

**설명**: 서버 처리 상태 전달

**데이터 구조**:
```json
{
  "type": "status",
  "data": {
    "state": "processing",
    "message": "ASR 처리 중...",
    "progress": 50
  },
  "timestamp": "2026-01-14T12:34:57Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**상태 값**:
- `idle`: 대기 중
- `recording`: 녹음 중
- `processing`: 처리 중 (ASR, LLM)
- `executing`: 도구 실행 중
- `completed`: 완료
- `error`: 오류 발생

---

#### 2.7 `error` - 에러 메시지

**설명**: 처리 중 발생한 오류 전달

**데이터 구조**:
```json
{
  "type": "error",
  "data": {
    "error_code": "STT_FAILED",
    "message": "음성 인식에 실패했습니다. 다시 말씀해주세요.",
    "details": {
      "reason": "low_confidence",
      "confidence": 0.3
    },
    "recoverable": true
  },
  "timestamp": "2026-01-14T12:35:05Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**에러 코드**:
- `ASR_FAILED`: ASR 실패
- `LLM_ERROR`: LLM 호출 오류
- `TTS_FAILED`: TTS 실패
- `TOOL_TIMEOUT`: 도구 실행 시간 초과
- `INVALID_REQUEST`: 잘못된 요청
- `SESSION_EXPIRED`: 세션 만료

**필드 설명**:
- `recoverable`: 복구 가능 여부 (true면 재시도 가능)

---

#### 2.8 `heartbeat_ack` - Heartbeat 응답

**설명**: 클라이언트 heartbeat에 대한 응답

**데이터 구조**:
```json
{
  "type": "heartbeat_ack",
  "data": {
    "server_time": "2026-01-14T12:35:30Z"
  },
  "timestamp": "2026-01-14T12:35:30Z",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 통신 흐름 예시

### 시나리오 1: PTT 음성 인식 (쿠팡에서 우유 검색)

```
1. [Client] User holds SPACE key

2. [Client → Server] audio_chunk (녹음 중, 3초마다)
   {
     "type": "audio_chunk",
     "data": {
       "audio": "base64_encoded...",
       "seq": 1,
       "is_final": false
     }
   }
   → 서버: 버퍼에 누적 (transcribe 안함)

3. [Client] User releases SPACE key after 4.5 seconds

4. [Client → Server] audio_chunk (녹음 종료)
   {
     "type": "audio_chunk",
     "data": {
       "audio": "base64_encoded...",
       "seq": 2,
       "is_final": true
     }
   }
   → 서버: 전체 버퍼 (4.5초) transcribe

5. [Server → Client] asr_result
   {
     "text": "쿠팡에서 우유 검색해줘",
     "confidence": 0.95,
     "is_final": true,
     "segment_id": "seg_1"
   }

6. [Server → Client] llm_command
   {
     "intent": "search_product",
     "site": "coupang",
     "parameters": {
       "keyword": "우유"
     }
   }

... (이후 tool_call, mcp_result 등 동일)
```

### 시나리오 2: 짧은 녹음 (< 0.5초)

```
1. [Client] User taps SPACE briefly (0.2 seconds)

2. [Client] Skip audio, send signal only
   {
     "type": "audio_chunk",
     "data": {
       "audio": "",
       "seq": 1,
       "is_final": true
     }
   }
   → 서버: 버퍼 비어있음, 아무것도 안함

Client output:
[SKIP] Audio too short (0.20s < 0.5s), sending final signal only
```

### 시나리오 3: 긴 녹음 (> 3초)

```
1. [Client] User holds SPACE for 7 seconds

2. [Client → Server] audio_chunk (3초 시점)
   { "seq": 1, "is_final": false }  → 버퍼 누적

3. [Client → Server] audio_chunk (6초 시점)
   { "seq": 2, "is_final": false }  → 버퍼 누적

4. [Client → Server] audio_chunk (7초, 릴리즈)
   { "seq": 3, "is_final": true }   → 전체 7초 transcribe

5. [Server → Client] asr_result
   { "text": "...", "duration": 7.0 }
```

---

## 세션 관리

### 세션 생성
WebSocket 연결 시 자동으로 세션 ID 생성
- UUID v4 형식
- Redis 또는 메모리에 저장

### 세션 데이터
```python
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "optional_user_id",
  "created_at": "2026-01-14T12:34:56Z",
  "last_activity": "2026-01-14T12:35:30Z",
  "state": {
    "current_site": "coupang",
    "current_flow": null,
    "conversation_history": [...]
  }
}
```

### 세션 만료
- 비활동 30분 후 자동 만료
- Heartbeat로 연결 유지

---

## 에러 처리

### 재연결 로직

**클라이언트 측**:
```python
retry_count = 0
max_retries = 5
backoff = [1, 2, 5, 10, 30]  # 초

while retry_count < max_retries:
    try:
        await ws.connect()
        break
    except ConnectionError:
        await asyncio.sleep(backoff[retry_count])
        retry_count += 1
```

### 메시지 재전송

**순서 보장**:
- `audio_chunk`의 `sequence` 번호로 순서 확인
- 누락된 청크는 재요청

---

## 보안

### 인증 (선택)
```http
Authorization: Bearer <임시_토큰>
```

### 데이터 암호화
- WSS (WebSocket Secure) 사용 권장
- TLS 1.3 이상

### Rate Limiting
- 클라이언트당 초당 100개 메시지 제한
- 초과 시 `RATE_LIMIT_EXCEEDED` 에러

---

## 성능 최적화

### 청크 크기
- 오디오: 1024 프레임 (~64ms @ 16kHz)
- 너무 작으면 오버헤드 증가
- 너무 크면 지연 증가

### 압축
- 오디오: Base64 인코딩 전 gzip 압축
- JSON: 불필요한 공백 제거

### 버퍼링
- 서버 측에서 5초 버퍼링
- 네트워크 지연 보정

---

## 참고

- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
- WebSocket RFC: https://datatracker.ietf.org/doc/html/rfc6455
