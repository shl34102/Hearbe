# FastAPI AI 서버 ↔ MCP 데스크탑 앱 통신 명세서

> AI 서버와 MCP 앱 간 실시간 통신 플로우 및 메시지 포맷 정의

---

## 개요

이 문서는 **FastAPI AI 서버**와 **MCP 데스크탑 앱** 간의 통신 방식을 정의합니다.

### 핵심 원칙
- **WebSocket**: 양방향 실시간 통신 (오디오, 명령, 결과)
- **내부 호출**: AI 서버 내 모듈 간 통신 (STT → LLM → TTS)

---

## 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│                        AI 서버 (FastAPI)                         │
│                                                                  │
│   ┌─────────┐    내부 호출    ┌─────────┐    내부 호출   ┌──────┐│
│   │   STT   │ ─────────────►  │   LLM    │ ────────────► │  TTS ││
│   │(Whisper)│   (텍스트)      │ Planner │  (응답텍스트)  │      ││
│   └────▲────┘                 └────┬────┘                └───┬──┘│
│        │                           │                         │   │
└────────┼───────────────────────────┼─────────────────────────┼───┘
         │ audio_chunk               │ tool_calls              │ tts_audio
         │ (WebSocket)               │ (WebSocket)             │ (WebSocket)
         │                           ▼                         ▼
┌────────┴──────────────────────────────────────────────────────────┐
│                        MCP 데스크탑 앱                            │
│                                                                   │
│   ┌─────────┐      ┌───────────────┐      ┌─────────────┐         │
│   │  Audio  │      │    Browser    │      │   Audio     │         │
│   │Recorder │      │   Controller  │      │   Player    │         │
│   └─────────┘      │  (Playwright) │      └─────────────┘         │
│                    └───────────────┘                              │
└───────────────────────────────────────────────────────────────────┘
```

---

## 통신 요약

| 통신 구간 | 방식 | 포맷 |
|-----------|------|------|
| MCP 앱 → AI 서버 (오디오) | **WebSocket** | JSON (`audio_chunk`) |
| MCP 앱 → AI 서버 (실행결과) | **WebSocket** | JSON (`mcp_result` + `page_data`) |
| AI 서버 내 STT → LLM | **내부 함수 호출** | Python dict/Pydantic |
| AI 서버 내 LLM → TTS | **내부 함수 호출** | Python str (텍스트) |
| AI 서버 → MCP 앱 (명령) | **WebSocket** | JSON (`tool_calls`) |
| AI 서버 → MCP 앱 (음성) | **WebSocket** | JSON (`tts_audio` + base64) |

---

## WebSocket 연결

### 연결 URL
```
ws://서버주소:8000/ws
```

### 연결 수립
```python
# MCP 앱에서 연결
import websockets

async with websockets.connect("ws://localhost:8000/ws") as ws:
    # 세션 ID 수신
    init_msg = await ws.recv()
    session_id = json.loads(init_msg)["session_id"]
```

---

## WebSocket 메시지 포맷

### 기본 구조
```json
{
  "type": "메시지_타입",
  "data": { ... },
  "session_id": "uuid-v4",
  "timestamp": "2026-01-20T09:00:00Z"
}
```

---

## MCP 앱 → AI 서버 메시지

### 1. `audio_chunk` - 오디오 데이터 전송

사용자 음성 녹음 데이터를 AI 서버로 전송합니다.

```json
{
  "type": "audio_chunk",
  "data": {
    "audio": "base64_encoded_pcm16_data...",
    "sample_rate": 16000,
    "channels": 1,
    "format": "pcm16",
    "is_final": true
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-20T09:00:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `audio` | string | Base64 인코딩된 오디오 바이너리 |
| `sample_rate` | int | 샘플링 레이트 (Hz), 권장: 16000 |
| `channels` | int | 채널 수 (1=모노) |
| `format` | string | 오디오 포맷 (`pcm16`, `wav`) |
| `is_final` | bool | 녹음 완료 여부 (true면 STT 시작) |

---

### 2. `mcp_result` - MCP 명령 실행 결과

브라우저 자동화 실행 결과를 AI 서버로 전송합니다.

```json
{
  "type": "mcp_result",
  "data": {
    "request_id": "req_12345",
    "success": true,
    "results": [
      {
        "action": "goto",
        "success": true,
        "result": "navigated to https://www.coupang.com"
      },
      {
        "action": "fill",
        "success": true,
        "result": "filled input with '물티슈'"
      },
      {
        "action": "extract",
        "success": true,
        "result": { "products": [...] }
      }
    ],
    "page_data": {
      "url": "https://www.coupang.com/np/search?q=물티슈",
      "title": "물티슈 검색결과",
      "products": [
        {
          "index": 1,
          "name": "코스트코 물티슈 100매 x 10팩",
          "price": 15900,
          "original_price": 19900,
          "rating": 4.8,
          "review_count": 1234,
          "is_rocket": true,
          "seller": "쿠팡"
        }
      ]
    }
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**`page_data` 필드 (검색 결과)**:
- 1페이지의 **모든 상품 정보**를 포함
- 사이트별 셀렉터 매핑으로 추출
- 상위 5개만 TTS로 읽고, 나머지는 세션에 저장

---

### 3. `user_input` - 사용자 추가 입력

플로우 진행 중 사용자 응답을 전송합니다.

```json
{
  "type": "user_input",
  "data": {
    "text": "네",
    "flow_id": "coupang_checkout",
    "step_id": "address_confirm"
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## AI 서버 → MCP 앱 메시지

### 1. `tool_calls` - MCP 명령 배열

LLM이 생성한 브라우저 자동화 명령을 MCP 앱에 전송합니다.

```json
{
  "type": "tool_calls",
  "data": {
    "request_id": "req_12345",
    "commands": [
      {
        "action": "goto",
        "args": { "url": "https://www.coupang.com" },
        "desc": "쿠팡 접속"
      },
      {
        "action": "fill",
        "args": { "selector": "input[name='q']", "text": "물티슈" },
        "desc": "검색어 입력"
      },
      {
        "action": "press",
        "args": { "selector": "input[name='q']", "key": "Enter" },
        "desc": "검색 실행"
      },
      {
        "action": "wait",
        "args": { "ms": 1500 },
        "desc": "결과 로딩 대기"
      },
      {
        "action": "extract",
        "args": {
          "selector": ".search-product",
          "fields": ["name", "price", "rating", "review_count"],
          "limit": 20
        },
        "desc": "상품 정보 추출"
      }
    ]
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `request_id` | string | 요청 고유 ID (결과 매칭용) |
| `commands` | array | 순차 실행할 명령 배열 |
| `action` | string | 명령 타입 (goto, fill, click, press, wait, extract) |
| `args` | object | 명령별 인자 |
| `desc` | string | 명령 설명 (디버깅/로깅용) |

---

### 2. `tts_audio` - TTS 음성 데이터

LLM 응답을 음성으로 변환하여 MCP 앱에 전송합니다.

```json
{
  "type": "tts_audio",
  "data": {
    "audio": "base64_encoded_mp3_data...",
    "text": "검색 결과 20개를 찾았습니다. 상위 5개를 읽어드릴게요. 첫 번째, 코스트코 물티슈 100매 10팩, 가격 15,900원, 별점 4.8점...",
    "format": "mp3",
    "duration": 12.5,
    "has_more": true
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `audio` | string | Base64 인코딩된 오디오 |
| `text` | string | TTS 원본 텍스트 |
| `format` | string | 오디오 포맷 (`mp3`, `wav`) |
| `duration` | float | 재생 시간 (초) |
| `has_more` | bool | 더 읽을 내용이 있는지 |

---

### 3. `flow_step` - 플로우 단계 안내

결제/회원가입 등 플로우 진행 시 단계 정보를 전송합니다.

```json
{
  "type": "flow_step",
  "data": {
    "flow_id": "coupang_checkout",
    "current_step": 2,
    "total_steps": 5,
    "step_name": "address_confirm",
    "prompt": "배송지를 확인해주세요. 서울시 강남구 테헤란로 123으로 배송됩니다.",
    "options": ["네", "아니오", "배송지 변경"]
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## AI 서버 내부 통신

### STT → LLM (내부 함수 호출)

```python
# websocket/handlers.py

async def handle_audio_chunk(ws, message: dict, session: Session):
    """오디오 수신 → STT → LLM → 명령 전송"""
    
    audio_data = base64.decode(message["data"]["audio"])
    
    # 1. STT 처리 (내부 호출)
    stt_result = await stt_service.transcribe(audio_data)
    # 반환: {"text": "쿠팡에서 물티슈 검색해줘", "confidence": 0.95, "language": "ko"}
    
    # 2. LLM에 전달 (내부 호출)
    llm_result = await llm_service.generate_commands(
        user_input=stt_result["text"],
        current_url=session.current_url,
        context=session.context
    )
    # 반환: CommandResult (commands, response_text, requires_flow, flow_type)
    
    # 3. 명령 전송 (WebSocket → MCP 앱)
    await ws.send_json({
        "type": "tool_calls",
        "data": {
            "request_id": generate_request_id(),
            "commands": [cmd.to_dict() for cmd in llm_result.commands]
        },
        "session_id": session.id
    })
```

---

### MCP 결과 → TTS (검색 결과 처리)

```python
# websocket/handlers.py

async def handle_mcp_result(ws, message: dict, session: Session):
    """MCP 실행 결과 수신 → TTS 생성 → 음성 전송"""
    
    result = message["data"]
    page_data = result.get("page_data", {})
    
    # 검색 결과가 있는 경우
    if "products" in page_data:
        products = page_data["products"]
        
        # 1. 전체 상품을 세션에 저장 (더 읽기 위해)
        session.products = products
        session.read_index = 0
        
        # 2. 상위 5개 상품 요약 텍스트 생성
        summary_text = generate_product_summary(
            products=products[:5],
            total_count=len(products)
        )
        # "검색 결과 20개입니다. 상위 5개를 읽어드릴게요.
        #  첫 번째, 코스트코 물티슈 100매 10팩, 15,900원, 별점 4.8점.
        #  두 번째, ..."
        
        session.read_index = 5
        
        # 3. TTS 생성 (내부 호출)
        audio_data = await tts_service.synthesize(summary_text)
        
        # 4. 음성 전송 (WebSocket → MCP 앱)
        await ws.send_json({
            "type": "tts_audio",
            "data": {
                "audio": base64.encode(audio_data),
                "text": summary_text,
                "format": "mp3",
                "has_more": len(products) > 5
            },
            "session_id": session.id
        })
```

---

## 시나리오별 흐름

### 시나리오 1: 상품 검색 ("쿠팡에서 물티슈 검색해줘")

```
1. [MCP 앱] V키 눌러 녹음 시작
2. [MCP 앱] V키 떼어 녹음 종료
3. [MCP 앱 → AI 서버] audio_chunk 전송 (is_final: true)
4. [AI 서버 내부] STT: 음성 → "쿠팡에서 물티슈 검색해줘"
5. [AI 서버 내부] LLM: 텍스트 → [goto, fill, press, wait, extract] 명령 생성
6. [AI 서버 → MCP 앱] tool_calls 전송 (5개 명령)
7. [MCP 앱] Playwright로 브라우저 자동화 실행
8. [MCP 앱 → AI 서버] mcp_result 전송 (page_data에 상품 20개 포함)
9. [AI 서버 내부] 상위 5개 상품 요약 → TTS 생성
10. [AI 서버 → MCP 앱] tts_audio 전송
11. [MCP 앱] 스피커로 음성 재생
```

---

### 시나리오 2: 더 읽기 ("더 읽어줘")

```
1. [MCP 앱 → AI 서버] audio_chunk ("더 읽어줘")
2. [AI 서버 내부] STT → "더 읽어줘"
3. [AI 서버 내부] LLM: 세션에서 products[5:10] 읽기
4. [AI 서버 내부] 다음 5개 상품 요약 → TTS 생성
5. [AI 서버 → MCP 앱] tts_audio 전송 (has_more: true/false)
6. [MCP 앱] 스피커로 음성 재생
```

---

### 시나리오 3: 특정 상품 선택 ("세 번째 상품 장바구니에 담아줘")

```
1. [MCP 앱 → AI 서버] audio_chunk ("세 번째 상품 장바구니에 담아줘")
2. [AI 서버 내부] STT → "세 번째 상품 장바구니에 담아줘"
3. [AI 서버 내부] LLM: 
   - session.products[2] 참조 (세 번째 = index 2)
   - 장바구니 담기 명령 생성
4. [AI 서버 → MCP 앱] tool_calls (장바구니 담기 명령)
5. [MCP 앱] 브라우저에서 장바구니 담기 실행
6. [MCP 앱 → AI 서버] mcp_result (성공/실패)
7. [AI 서버 내부] TTS: "코스트코 물티슈를 장바구니에 담았습니다"
8. [AI 서버 → MCP 앱] tts_audio 전송
```

---

## 사이트별 상품 정보 추출 셀렉터

### 쿠팡
```json
{
  "product_list": ".search-product",
  "product_name": ".name",
  "product_price": ".price-value",
  "product_rating": ".rating",
  "product_review": ".rating-total-count",
  "is_rocket": ".badge-rocket"
}
```

### 네이버쇼핑
```json
{
  "product_list": ".product_item",
  "product_name": ".product_title",
  "product_price": ".price em",
  "product_mall": ".mall_title"
}
```

### 11번가
```json
{
  "product_list": ".c_product_info",
  "product_name": ".c_product_info_title",
  "product_price": ".c_product_info_price"
}
```

---

## 세션 데이터 구조

```python
class Session:
    id: str                    # 세션 ID
    current_url: str           # 현재 페이지 URL
    current_site: str          # 현재 사이트 (coupang, naver, 11st)
    products: List[Product]    # 검색된 상품 목록 (전체)
    read_index: int            # 읽은 상품 인덱스
    flow_context: FlowContext  # 진행 중인 플로우 정보
    context: dict              # 대화 컨텍스트 (이전 발화 등)
```

---

## 오류 처리

### AI 서버 → MCP 앱 오류 메시지

```json
{
  "type": "error",
  "data": {
    "error_code": "STT_FAILED",
    "message": "음성 인식에 실패했습니다. 다시 말씀해주세요.",
    "recoverable": true
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| error_code | 설명 | 복구 가능 |
|------------|------|----------|
| `STT_FAILED` | 음성 인식 실패 | ✅ |
| `LLM_ERROR` | LLM 호출 오류 | ✅ |
| `TTS_FAILED` | TTS 생성 실패 | ✅ |
| `INVALID_COMMAND` | 알 수 없는 명령 | ✅ |
| `SESSION_EXPIRED` | 세션 만료 | ❌ |

---

**문서 버전**: 1.0  
**작성일**: 2026-01-20  
**담당자**: 김재환
